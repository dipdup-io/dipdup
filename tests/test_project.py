import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from dipdup import env
from dipdup.exceptions import ConfigurationError
from dipdup.project import Answers
from dipdup.project import answers_from_replay
from dipdup.project import get_default_answers
from dipdup.project import render_base
from dipdup.project import render_project

PACKAGE = 'test_indexer'
WORKFLOWS = ('.github/workflows/test.yml', '.github/workflows/build.yml')
DEPENDABOT = '.github/dependabot.yml'
LAUNCH = '.vscode/launch.json'

yaml = YAML(typ='safe')


@pytest.fixture
def project_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    # NOTE: Package path is cached per process; each test renders into its own tmp_path
    env.get_package_path.cache_clear()
    monkeypatch.chdir(tmp_path)
    yield tmp_path / PACKAGE
    env.get_package_path.cache_clear()


def _answers(**kwargs: str) -> Answers:
    answers = get_default_answers(PACKAGE)
    answers.update(kwargs)  # type: ignore[typeddict-item]
    return answers


def _write_replay(path: Path, **kwargs: str) -> Path:
    lines = ['spec_version: 3.0', 'replay:', f'  package: {PACKAGE}']
    lines += [f'  {k}: {v}' for k, v in kwargs.items()]
    path.write_text('\n'.join(lines) + '\n')
    return path


def test_defaults_render_no_addons(project_path: Path) -> None:
    render_project(_answers())

    assert (project_path / 'Makefile').is_file()
    assert not (project_path / '.github').exists()
    assert not (project_path / '.vscode').exists()


def test_ci_github(project_path: Path) -> None:
    render_project(_answers(ci='github'))

    for workflow in WORKFLOWS:
        content = yaml.load((project_path / workflow).read_text())
        assert content['name'] == Path(workflow).stem.capitalize()

    dependabot = yaml.load((project_path / DEPENDABOT).read_text())
    assert dependabot['updates'][0]['package-ecosystem'] == 'github-actions'
    assert not (project_path / '.vscode').exists()


def test_ide_vscode(project_path: Path) -> None:
    render_project(_answers(ide='vscode'))

    lines = (project_path / LAUNCH).read_text().splitlines()
    launch = json.loads('\n'.join(line for line in lines if not line.strip().startswith('//')))
    assert [c['name'] for c in launch['configurations']] == ['DipDup: run', 'DipDup: attach']
    assert not (project_path / '.github').exists()


def test_ci_github_non_uv_skips_test_workflow(project_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    render_project(_answers(ci='github', package_manager='poetry'))

    assert not (project_path / '.github/workflows/test.yml').exists()
    assert (project_path / '.github/workflows/build.yml').is_file()
    assert (project_path / DEPENDABOT).is_file()
    assert 'uv projects only' in capsys.readouterr().out


def test_render_base_adopts_addons(project_path: Path) -> None:
    render_project(_answers())
    replay_path = project_path / 'configs' / 'replay.yaml'
    replay_path.write_text(replay_path.read_text().replace('ci: none', 'ci: github'))

    render_base(answers_from_replay(replay_path))

    for path in (*WORKFLOWS, DEPENDABOT):
        assert (project_path / path).is_file()
    assert not (project_path / '.vscode').exists()

    build_path = project_path / '.github/workflows/build.yml'
    build_path.write_text('# edited\n')

    render_base(answers_from_replay(replay_path))
    assert build_path.read_text() == '# edited\n'

    render_base(answers_from_replay(replay_path), force=True)
    assert build_path.read_text() != '# edited\n'


def test_render_base_include(project_path: Path) -> None:
    render_project(_answers(ci='github', ide='vscode'))
    for path in (*WORKFLOWS, DEPENDABOT, LAUNCH, 'Makefile'):
        (project_path / path).write_text('# edited\n')

    render_base(_answers(ci='github', ide='vscode'), force=True, include={'.github'})

    for path in (*WORKFLOWS, DEPENDABOT):
        assert (project_path / path).read_text() != '# edited\n'
    for path in (LAUNCH, 'Makefile'):
        assert (project_path / path).read_text() == '# edited\n'


def test_replay_without_new_keys(tmp_path: Path) -> None:
    answers = answers_from_replay(_write_replay(tmp_path / 'replay.yaml'))

    assert answers['ci'] == 'none'
    assert answers['ide'] == 'none'


@pytest.mark.parametrize('key', ['ci', 'ide'])
def test_replay_invalid_value(tmp_path: Path, key: str) -> None:
    replay_path = _write_replay(tmp_path / 'replay.yaml', **{key: 'gitlab'})

    with pytest.raises(ConfigurationError) as exc_info:
        answers_from_replay(replay_path)
    assert f'replay.{key}' in exc_info.value.msg
