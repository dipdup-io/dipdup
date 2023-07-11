"""Scaffolding tools and scenarios for `dipdup new` command.

Ask user some question with Click; render Jinja2 templates with answers.
"""
import logging
import re
from copy import copy
from pathlib import Path
from typing import TypedDict
from typing import TypeVar

import asyncclick as cl
import survey  # type: ignore[import]
from pydantic.dataclasses import dataclass
from tabulate import tabulate

from dipdup import __version__
from dipdup.utils import load_template
from dipdup.utils import write
from dipdup.yaml import DipDupYAMLConfig

_logger = logging.getLogger('dipdup.project')


TEZOS_DEMOS = (
    ('demo_domains', 'Tezos Domains name service'),
    ('demo_big_maps', 'Indexing specific big maps'),
    ('demo_events', 'Processing contract events'),
    ('demo_head', 'Processing head block metadata'),
    ('demo_nft_marketplace', 'hic at nunc NFT marketplace'),
    ('demo_dex', 'Quipuswap DEX balances and liquidity'),
    ('demo_factories', 'Example of spawning indexes in runtime'),
    ('demo_dao', 'Homebase DAO registry'),
    ('demo_token', 'TzBTC FA1.2 token operations'),
    ('demo_token_transfers', 'TzBTC FA1.2 token transfers'),
    ('demo_auction', 'TzColors NFT marketplace'),
    ('demo_raw', 'Process raw operations without filtering and strict typing (experimental)'),
)
EVM_DEMOS = (
    ('demo_evm_events', 'Very basic indexer for USDt transfers'),
    ('demo_uniswap', 'Uniswap V3 pools, positions, swaps, ticks, etc.'),
)
OTHER_DEMOS = (
    ('demo_blank', 'Empty config for a fresh start'),
    # TODO: demo_jobs
    # TODO: demo_backup
    # TODO: demo_sql
    # TODO: demo_timescale
)


_T = TypeVar('_T')


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
    template='demo_dao',
    package='dipdup_indexer',
    version='0.0.1',
    description='Blockchain indexer built with DipDup',
    license='MIT',
    name='John Smith',
    email='john_smith@localhost.lan',
    postgresql_image='postgres:15',
    # TODO: fetch latest from GH
    hasura_image='hasura/graphql-engine:v2.29.1',
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
    answers = copy(DEFAULT_ANSWERS)

    welcome_text = (
        '\n'
        'Welcome to DipDup! This command will help you to create a new project.\n'
        'You can abort at any time by pressing Ctrl+C. Press Enter to use default value.\n'
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
    templates = (EVM_DEMOS, TEZOS_DEMOS, OTHER_DEMOS)[group_index]

    # list of options can contain folder name of template or folder name of template with description
    # all project templates are in src/dipdup/projects
    _, answers['template'] = prompt_anyof(
        'Choose a project template:',
        options=tuple(i[0] for i in templates),
        comments=tuple(i[1] for i in templates),
        default=0,
    )

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
        "Enter author's name",
        value=answers['name'],
    )
    answers['email'] = survey.routines.input(
        "Enter author's email",
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
    answers = Replay(**replay_config).replay
    return copy(DEFAULT_ANSWERS) | answers


def render_project(
    answers: Answers,
    force: bool = False,
) -> None:
    """Render project from template"""
    # NOTE: Common base
    _render_templates(answers, Path('base'), force)

    # NOTE: Config and handlers
    _render_templates(answers, Path(answers['template']), force)


def _render_templates(answers: Answers, path: Path, force: bool = False) -> None:
    from jinja2 import Template

    project_path = Path(__file__).parent / 'projects' / path
    project_paths = project_path.glob('**/*.j2')

    for path in project_paths:
        template_path = path.relative_to(Path(__file__).parent)
        output_path = Path(
            answers['package'],
            *path.relative_to(project_path).parts,
            # NOTE: Remove ".j2" from extension
        ).with_suffix(path.suffix[:-3])
        output_path = Path(Template(str(output_path)).render(project=answers))
        _render(answers, template_path, output_path, force)


def _render(answers: Answers, template_path: Path, output_path: Path, force: bool) -> None:
    if output_path.exists() and not force:
        _logger.warning('File `%s` already exists, skipping', output_path)

    _logger.info('Generating `%s`', output_path)
    template = load_template(str(template_path))
    content = template.render(project=answers)
    write(output_path, content, overwrite=force)
