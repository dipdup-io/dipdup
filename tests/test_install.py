import subprocess
from pathlib import Path
from typing import Any

import pytest

from dipdup import install


def test_is_uv_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / 'dipdup').mkdir()

    def _uv_tool_dir(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert args[0] == ('uv', 'tool', 'dir')
        return subprocess.CompletedProcess(args[0], 0, stdout=f'{tmp_path}\n', stderr='')

    monkeypatch.setattr(subprocess, 'run', _uv_tool_dir)

    assert install.is_uv_tool('dipdup') is True
    assert install.is_uv_tool('not-installed') is False


def test_is_uv_tool_without_uv(monkeypatch: pytest.MonkeyPatch) -> None:
    def _failed(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args[0], 2, stdout='', stderr='error')

    monkeypatch.setattr(subprocess, 'run', _failed)

    assert install.is_uv_tool('dipdup') is False


def test_update_bails_out_when_not_uv_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[tuple[str, ...]] = []

    monkeypatch.setattr(install, 'prepare', lambda: None)
    monkeypatch.setattr(install, 'is_uv_tool', lambda _: False)
    monkeypatch.setattr(install, 'run_cmd', lambda *args, **kwargs: commands.append(args))

    with pytest.raises(SystemExit) as e:
        install.install(quiet=True, force=False, version=None, ref=None, path=None, update=True)

    assert e.value.code == 1
    # NOTE: `uv tool upgrade` would have reported DipDup as not installed at all
    assert not commands


def test_update_upgrades_uv_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[tuple[str, ...]] = []

    monkeypatch.setattr(install, 'prepare', lambda: None)
    monkeypatch.setattr(install, 'is_uv_tool', lambda _: True)
    monkeypatch.setattr(install, 'run_cmd', lambda *args, **kwargs: commands.append(args))

    with pytest.raises(SystemExit) as e:
        install.install(quiet=True, force=False, version=None, ref=None, path=None, update=True)

    assert e.value.code == 0
    assert commands == [('uv', 'tool', 'upgrade', 'dipdup')]


@pytest.mark.parametrize(
    ('kwargs', 'expected'),
    (
        ({}, ('uv', 'tool', 'install', 'dipdup')),
        ({'version': '8.6.0'}, ('uv', 'tool', 'install', 'dipdup==8.6.0')),
        ({'ref': 'next'}, ('uv', 'tool', 'install', f'git+{install.GITHUB}@next')),
        ({'path': '.'}, ('uv', 'tool', 'install', '.')),
        ({'force': True}, ('uv', 'tool', 'install', 'dipdup', '--force')),
        ({'pre': True}, ('uv', 'tool', 'install', 'dipdup', '--prerelease', 'allow')),
    ),
)
def test_install_sources(
    kwargs: dict[str, Any],
    expected: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []

    monkeypatch.setattr(install, 'prepare', lambda: None)
    # NOTE: DipDup is already on PATH; an explicit source must still be honored
    monkeypatch.setattr(install, 'which', lambda *args, **kwargs: '/usr/local/bin/dipdup')
    monkeypatch.setattr(install, 'run_cmd', lambda *args, **kwargs: commands.append(args))

    with pytest.raises(SystemExit):
        install.install(**{'quiet': True, 'force': False, 'version': None, 'ref': None, 'path': None, **kwargs})

    assert commands == [expected]
