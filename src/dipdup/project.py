"""Scaffolding tools and scenarios for `dipdup new` command.

Ask user some question with Click; render Jinja2 templates with answers.
"""
import logging
import re
from copy import copy
from pathlib import Path
from typing import TypedDict

import asyncclick as cl
import survey  # type: ignore[import]
from pydantic.dataclasses import dataclass
from tabulate import tabulate

from dipdup import __version__
from dipdup.env import get_package_path
from dipdup.utils import load_template
from dipdup.utils import write
from dipdup.yaml import DipDupYAMLConfig

_logger = logging.getLogger(__name__)


TEMPLATES: dict[str, tuple[str, ...]] = {
    'evm': (
        'demo_evm_events',
        'demo_uniswap',
    ),
    'tezos': (
        'demo_domains',
        'demo_big_maps',
        'demo_events',
        'demo_head',
        'demo_nft_marketplace',
        'demo_dex',
        'demo_factories',
        'demo_dao',
        'demo_token',
        'demo_token_transfers',
        'demo_auction',
        'demo_raw',
    ),
    'other': ('demo_blank',),
}

# TODO: demo_jobs
# TODO: demo_backup
# TODO: demo_sql
# TODO: demo_timescale


class Answers(TypedDict):
    """Survey answers"""

    dipdup_version: str
    template: str
    package: str
    version: str
    description: str
    license: str
    name: str
    email: str
    postgresql_image: str
    hasura_image: str
    line_length: str


@dataclass
class Replay:
    spec_version: str | float
    replay: Answers


DEFAULT_ANSWERS = Answers(
    dipdup_version=__version__.split('.')[0],
    template='demo_blank',
    package='dipdup_indexer',
    version='0.0.1',
    description='A blockchain indexer built with DipDup',
    license='MIT',
    name='John Doe',
    email='john_doe@example.com',
    postgresql_image='postgres:15',
    # TODO: fetch latest from GH
    hasura_image='hasura/graphql-engine:v2.30.1',
    line_length='120',
)


def prompt_anyof(
    question: str,
    options: tuple[str, ...],
    comments: tuple[str, ...],
    default: int,
) -> tuple[int, str]:
    """Ask user to choose one of options; returns index and value"""
    table = tabulate(
        zip(options, comments),
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
    welcome_text = (
        '\n'
        'Welcome to DipDup! This command will help you to create a new project.\n'
        'You can abort at any time by pressing Ctrl+C twice. Press Enter to use default value.\n'
    )
    cl.secho(welcome_text, fg='yellow')

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

    # list of options can contain folder name of template or folder name of template with description
    # all project templates are in src/dipdup/projects
    _, template = prompt_anyof(
        'Choose a project template:',
        options=tuple(options),
        comments=tuple(comments),
        default=0,
    )
    answers = copy(DEFAULT_ANSWERS)
    answers['template'] = template

    while True:
        package = survey.routines.input(
            'Enter project name (the name will be used for folder name and package name): ',
            value=answers['package'],
        )
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', package):
            break

        cl.secho(
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

    # define author and license for new indexer
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

    cl.secho('\n' + 'Now choose versions of software you want to use.' + '\n', fg='yellow')

    _, answers['postgresql_image'] = prompt_anyof(
        question='Choose PostgreSQL version. Try TimescaleDB when working with time series.',
        options=(
            'postgres:15',
            'timescale/timescaledb:latest-pg15',
            'timescale/timescaledb-ha:pg15-latest',
        ),
        comments=(
            'PostgreSQL',
            'TimescaleDB',
            'TimescaleDB HA',
        ),
        default=0,
    )

    cl.secho(
        '\n' + 'Miscellaneous tunables; leave default values if unsure' + '\n',
        fg='yellow',
    )

    answers['line_length'] = survey.routines.input(
        'Enter maximum line length for linters: ',
        value=answers['line_length'],
    )
    return answers


def answers_from_replay(path: Path) -> Answers:
    replay_config, _ = DipDupYAMLConfig.load([path])
    answers = copy(DEFAULT_ANSWERS)
    answers.update(replay_config['replay'])
    return answers


def render_project(
    answers: Answers,
    force: bool = False,
) -> None:
    """Render project from template"""
    # NOTE: Common base
    _render_templates(answers, Path('base'), force)

    # NOTE: Config and handlers
    _render_templates(answers, Path(answers['template']), force)

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
) -> None:
    """Render base from template"""
    # NOTE: Common base
    _render_templates(answers, Path('base'), force, refresh=True)

    _render(
        answers,
        template_path=Path(__file__).parent / 'templates' / 'replay.yaml.j2',
        output_path=Path('configs') / 'replay.yaml',
        force=force,
    )


def _render_templates(answers: Answers, path: Path, force: bool = False, refresh: bool = False) -> None:
    from jinja2 import Template

    project_path = Path(__file__).parent / 'projects' / path
    project_paths = project_path.glob('**/*.j2')

    for path in project_paths:
        template_path = path.relative_to(Path(__file__).parent)
        output_base = get_package_path(answers['package']) if refresh else Path(answers['package'])
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
    content = template.render(project=answers)
    write(output_path, content, overwrite=force)
