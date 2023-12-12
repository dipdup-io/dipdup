"""Scaffolding tools and scenarios for `dipdup new` command.

Ask user some question with Click; render Jinja2 templates with answers.
"""

import logging
import re
from pathlib import Path
from typing import TypedDict

from pydantic.dataclasses import dataclass
from tabulate import tabulate

from dipdup import __version__
from dipdup.cli import big_yellow_echo
from dipdup.cli import echo
from dipdup.env import get_package_path
from dipdup.env import get_pyproject_name
from dipdup.utils import load_template
from dipdup.utils import write
from dipdup.yaml import DipDupYAMLConfig

_logger = logging.getLogger(__name__)


# NOTE: All templates are stored in src/dipdup/projects
TEMPLATES: dict[str, tuple[str, ...]] = {
    'evm': (
        'demo_evm_events',
        'demo_uniswap',
    ),
    'tezos': (
        'demo_auction',
        'demo_big_maps',
        'demo_dao',
        'demo_dex',
        'demo_domains',
        'demo_events',
        'demo_etherlink',
        'demo_factories',
        'demo_head',
        'demo_nft_marketplace',
        'demo_raw',
        'demo_token',
        'demo_token_transfers',
    ),
    'other': ('demo_blank',),
}

# TODO: demo_jobs
# TODO: demo_backup
# TODO: demo_sql
# TODO: demo_timescale
# TODO: demo_cli


class Answers(TypedDict):
    """Answers for survey/replay in order of appearance"""

    dipdup_version: str
    template: str
    package: str
    version: str
    description: str
    license: str
    name: str
    email: str
    postgres_image: str
    postgres_data_path: str
    hasura_image: str
    line_length: str
    package_manager: str


def get_default_answers() -> Answers:
    return Answers(
        dipdup_version=__version__.split('.')[0],
        template='demo_blank',
        package='dipdup_indexer',
        version='0.0.1',
        description='A blockchain indexer built with DipDup',
        license='MIT',
        name='John Doe',
        email='john_doe@example.com',
        postgres_image='postgres:15',
        postgres_data_path='/var/lib/postgresql/data',
        hasura_image='hasura/graphql-engine:latest',
        line_length='120',
        package_manager='pdm',
    )


def get_package_answers(package: str | None = None) -> Answers | None:
    if not package:
        package = get_pyproject_name()
    if not package:
        return None

    replay_path = get_package_path(package) / 'configs' / 'replay.yaml'
    if not replay_path.is_file():
        return None

    return answers_from_replay(replay_path)


@dataclass
class ReplayConfig:
    spec_version: str | float
    replay: Answers


def prompt_anyof(
    question: str,
    options: tuple[str, ...],
    comments: tuple[str, ...],
    default: int,
) -> tuple[int, str]:
    """Ask user to choose one of options; returns index and value"""
    import survey  # type: ignore[import-untyped]

    table = tabulate(
        zip(options, comments, strict=True),
        tablefmt='plain',
    )
    index = survey.routines.select(
        question + '\n',
        options=table.split('\n'),
        index=default,
    )
    return index, options[index]


def answers_from_terminal() -> Answers:
    """Script running on dipdup new command and will create a new project base from interactive survey"""
    import survey

    big_yellow_echo(
        'Welcome to DipDup! This command will help you to create a new project.\n'
        'You can abort at any time by pressing Ctrl+C twice. Press Enter to use default value.'
    )

    group_index, _ = prompt_anyof(
        question='What blockchain are you going to index?',
        options=(
            'EVM',
            'Tezos',
            '[none]',
        ),
        comments=(
            'EVM-compatible blockchains',
            'Tezos',
            'Create project from scratch or learn advanced DipDup features',
        ),
        default=0,
    )
    template_group = (
        TEMPLATES['evm'],
        TEMPLATES['tezos'],
        TEMPLATES['other'],
    )[group_index]

    options, comments = [], []
    for name in template_group:
        replay_path = Path(__file__).parent / 'projects' / name / 'replay.yaml'
        _answers = answers_from_replay(replay_path)
        options.append(_answers['template'])
        comments.append(_answers['description'])

    _, template = prompt_anyof(
        'Choose a project template:',
        options=tuple(options),
        comments=tuple(comments),
        default=0,
    )
    answers = get_default_answers()
    answers['template'] = template

    while True:
        package = survey.routines.input(
            'Enter project name (the name will be used for folder name and package name): ',
            value=answers['package'],
        )
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', package):
            break

        echo(
            f'"{package}" is not valid Python package name. Please use only letters, numbers and underscores.',
            fg='red',
        )

    answers['package'] = package
    answers['version'] = survey.routines.input(
        'Enter project version: ',
        value=answers['version'],
    )

    # NOTE: Used in pyproject.toml, README.md and some other places
    answers['description'] = survey.routines.input(
        'Enter project description: ',
        value=answers['description'],
    )

    answers['license'] = survey.routines.input(
        'Enter project license (DipDup itself is MIT-licensed.): ',
        value=answers['license'],
    )

    answers['name'] = survey.routines.input(
        "Enter author's name: ",
        value=answers['name'],
    )
    answers['email'] = survey.routines.input(
        "Enter author's email: ",
        value=answers['email'],
    )

    big_yellow_echo('Now choose versions of software you want to use.')

    _, answers['postgres_image'] = prompt_anyof(
        question='Choose PostgreSQL version. Try TimescaleDB when working with time series.',
        options=(
            'postgres:15',
            'timescale/timescaledb:latest-pg15',
            'timescale/timescaledb-ha:pg15',
        ),
        comments=(
            'PostgreSQL',
            'TimescaleDB',
            'TimescaleDB HA',
        ),
        default=0,
    )
    if 'timescaledb-ha' in answers['postgres_image']:
        answers['postgres_data_path'] = '/home/postgres/pgdata/data'
        echo(
            '`timescaledb-ha` Docker image uses `/home/postgres/pgdata/data` as a data path; generated files were updated accordingly.',
            fg='yellow',
        )

    big_yellow_echo('Miscellaneous tunables; leave default values if unsure')

    _, answers['package_manager'] = prompt_anyof(
        question='Choose package manager',
        options=(
            'pdm',
            'poetry',
            'none',
        ),
        comments=(
            'PDM',
            'Poetry',
            '[none]',
        ),
        default=0,
    )

    answers['line_length'] = survey.routines.input(
        'Enter maximum line length for linters: ',
        value=answers['line_length'],
    )
    return answers


def answers_from_replay(path: Path) -> Answers:
    yaml_config, _ = DipDupYAMLConfig.load([path])
    yaml_config['replay'] = {
        **get_default_answers(),
        **yaml_config['replay'],
    }
    return ReplayConfig(**yaml_config).replay


def render_project(
    answers: Answers,
    force: bool = False,
) -> None:
    """Render project from template"""
    # NOTE: Common base
    _render_templates(answers, Path('base'), force)

    # NOTE: Config and handlers
    _render_templates(answers, Path(answers['template']), force)

    # NOTE: Replay to use with `init --base` and `new --replay`
    Path(answers['package']).joinpath('configs').mkdir(parents=True, exist_ok=True)
    _render(
        answers,
        template_path=Path(__file__).parent / 'templates' / 'replay.yaml.j2',
        output_path=Path(answers['package']) / 'configs' / 'replay.yaml',
        force=force,
    )


def render_base(
    answers: Answers,
    force: bool = False,
    include: set[str] | None = None,
) -> None:
    """Render base from template"""
    # NOTE: Render common base
    _render_templates(
        answers=answers,
        path=Path('base'),
        force=force,
        include=include,
        exists=True,
    )
    # NOTE: Don't forget to update replay.yaml with new values
    _render(
        answers=answers,
        template_path=Path(__file__).parent / 'templates' / 'replay.yaml.j2',
        output_path=Path('configs') / 'replay.yaml',
        force=force,
    )


def _render_templates(
    answers: Answers,
    path: Path,
    force: bool = False,
    include: set[str] | None = None,
    exists: bool = False,
) -> None:
    from jinja2 import Template

    project_path = Path(__file__).parent / 'projects' / path
    project_paths = project_path.glob('**/*.j2')

    for path in project_paths:
        template_path = path.relative_to(Path(__file__).parent)
        relative_path = str(Path(*template_path.parts[2:]))[:-3]

        if include and not any(relative_path.startswith(i) for i in include):
            continue

        output_base = get_package_path(answers['package']) if exists else Path(answers['package'])
        output_path = Path(
            output_base,
            *path.relative_to(project_path).parts,
            # NOTE: Remove ".j2" from extension
        ).with_suffix(path.suffix[:-3])
        output_path = Path(Template(str(output_path)).render(project=answers))
        _render(answers, template_path, output_path, force)


def _render(answers: Answers, template_path: Path, output_path: Path, force: bool) -> None:
    if output_path.exists() and not force:
        _logger.info('File `%s` already exists, skipping', output_path)

    _logger.info('Generating `%s`', output_path)
    template = load_template(str(template_path))
    content = template.render(
        project=answers,
        __version__=__version__,
    )
    write(output_path, content, overwrite=force)
