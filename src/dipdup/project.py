"""Scaffolding tools and scenarios for `dipdup new` command.

Ask user some question with Click; render Jinja2 templates with answers.
"""
import logging
import re
from copy import copy
from pathlib import Path
from typing import Any
from typing import TypedDict
from typing import TypeVar

import asyncclick as cl
import orjson
from tabulate import tabulate

from dipdup import __version__
from dipdup.utils import load_template
from dipdup.utils import write

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
    ('blank', 'Empty config for a fresh start'),
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
    project_name: str
    package: str
    version: str
    description: str
    license: str
    author: str
    postgresql_image: str
    hasura_image: str
    crash_reporting: bool
    linters: str
    line_length: str


DEFAULT_ANSWERS = Answers(
    dipdup_version=__version__.split('.')[0],
    template='demo_dao',
    project_name='dipdup_indexer',
    package='dipdup_indexer',
    version='0.0.1',
    description='Blockchain indexer built with DipDup',
    license='MIT',
    author='John Smith <john_smith@localhost.lan>',
    postgresql_image='postgres:15',
    # TODO: fetch latest from GH
    hasura_image='hasura/graphql-engine:v2.26.0',
    crash_reporting=False,
    linters='default',
    line_length='120',
)


def prompt(
    text: str,
    default: Any,
    type_: type[_T],
    print_default: bool = True,
) -> _T:
    """Ask user something with casting to type; print_default=True prints default choise be used"""
    try:
        value: _T = cl.prompt(
            text=f'{text} [{default}]' if print_default else text,
            default=default,
            type=type_,
            show_default=False,
        )
        cl.echo('\n')
        return value
    except cl.Abort:
        cl.echo('\nAborted')
        quit(0)


def prompt_anyof(
    question: str,
    options: tuple[str, ...],
    comments: tuple[str, ...],
    default: int,
) -> tuple[int, str]:
    """Ask user to choose one of options; returns index and value"""
    table = tabulate(
        zip(range(len(options)), options, comments),
        colalign=('right', 'left', 'left'),
        tablefmt='simple_outline',
    )
    cl.secho(f'=> {question}', fg='blue')
    cl.echo(table)

    index = prompt('Please choose an option', default, type_=int)
    return index, options[index]


def prompt_str(
    question: str,
    default: str,
) -> str:
    """Blue prompt in dipdup style for str answers"""
    cl.secho(f'=> {question}', fg='blue')
    return prompt(f'[{default}]', default, str, print_default=False)


def prompt_bool(
    question: str,
    default: bool,
) -> bool:
    """Blue prompt in dipdup style for bool answers"""
    cl.secho(f'=> {question}', fg='blue')
    default_str = ' [Y/n]' if default else ' [y/N]'
    return prompt(default_str, default, bool, print_default=False)

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
        'Choose a project template',
        options=tuple(i[0] for i in templates),
        comments=tuple(i[1] for i in templates),
        default=0,
    )

    project_name = prompt_str(
        'Enter project name (the name will be used for folder name and package name)',
        answers['project_name'],
    )
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', project_name):
        cl.secho(
            f'"{project_name}" is not valid Python package name. Please use only letters, numbers and underscores.',
            fg='red',
        )
        quit(1)
    answers['project_name'] = project_name
    answers['package'] = project_name

    answers['version'] = prompt_str(
        'Enter project version',
        answers['version'],
    )

    # NOTE: Used in pyproject.toml, README.md and some other places
    answers['description'] = prompt_str(
        'Enter project description',
        answers['description'],
    )

    # define author and license for new indexer
    answers['license'] = prompt_str(
        'Enter project license\n' 'DipDup itself is MIT-licensed.',
        answers['license'],
    )
    answers['author'] = prompt_str(
        ('Enter project author\n' 'You can add more later in pyproject.toml.'),
        answers['author'],
    )

    cl.secho('\n' + 'Now choose versions of software you want to use.' + '\n', fg='yellow')

    _, answers['postgresql_image'] = prompt_anyof(
        question=('Choose PostgreSQL version\n' 'Try TimescaleDB when working with time series.'),
        options=(
            'postgres:15',
            'timescale/timescaledb:latest-pg15',
            'timescale/timescaledb-ha:pg15-latest',
            'sqlite',
        ),
        comments=(
            'PostgreSQL',
            'TimescaleDB',
            'TimescaleDB HA (more extensions)',
            'Sqlite (simplified in-memory configuration)',
        ),
        default=0,
    )

    cl.secho('\n' + 'Miscellaneous tunables; leave default values if unsure' + '\n', fg='yellow')

    answers['crash_reporting'] = prompt_bool(
        'Enable crash reporting?\n' 'It helps us a lot to improve DipDup',
        answers['crash_reporting'],
    )

    _, answers['linters'] = prompt_anyof(
        'Choose tools to lint and test your code\n' 'You can always add more later in pyproject.toml.',
        ('default', 'none'),
        ('Swiss knife of modern Python: black, ruff, mypy', 'None'),
        default=0,
    )

    answers['line_length'] = prompt_str(
        ('Enter maximum line length\n' 'Used by linters.'),
        default=answers['line_length'],
    )
    return answers


def write_cookiecutter_json(answers: Answers, path: Path) -> None:
    values = {k: v for k, v in answers.items() if not k.startswith('_')}
    path.write_bytes(
        orjson.dumps(
            values,
            option=orjson.OPT_INDENT_2,
        )
    )


def answers_from_replay(path: Path) -> Answers:
    if not path.is_file() and path.suffix != '.json':
        raise Exception

    replay_answers: Answers = orjson.loads(path.read_bytes())
    return copy(DEFAULT_ANSWERS) | replay_answers


def render_project(
    answers: Answers,
    force: bool = False,
) -> None:
    """Render project from template"""
    # NOTE: Common base
    _render_templates(answers, Path('base'), force)

    # NOTE: Config and handlers
    _render_templates(answers, Path(answers['template']), force)

    # NOTE: Linters and stuff
    _render_templates(answers, Path('linters_' + answers['linters']), force)


def _render_templates(answers: Answers, path: Path, force: bool = False) -> None:
    from jinja2 import Template

    project_path = Path(__file__).parent / 'projects' / path
    project_paths = project_path.glob('**/*.j2')

    for path in project_paths:
        template_path = path.relative_to(Path(__file__).parent)
        output_path = Path(
            answers['project_name'],
            *path.relative_to(project_path).parts,
            # NOTE: Remove ".j2" from extension
        ).with_suffix(path.suffix[:-3])
        output_path = Path(Template(str(output_path)).render(cookiecutter=answers))
        _render(answers, template_path, output_path, force)


def _render(answers: Answers, template_path: Path, output_path: Path, force: bool) -> None:
    if output_path.exists() and not force:
        _logger.warning('File `%s` already exists, skipping', output_path)

    _logger.info('Generating `%s`', output_path)
    template = load_template(str(template_path))
    content = template.render(cookiecutter=answers)
    write(output_path, content, overwrite=force)
