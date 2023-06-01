import logging
from copy import copy
from pathlib import Path
from typing import Any
from typing import Type
from typing import TypedDict
from typing import TypeVar
from typing import cast

import asyncclick as cl
import orjson
from tabulate import tabulate

from dipdup import __version__
from dipdup.utils import load_template
from dipdup.utils import write

_logger = logging.getLogger('dipdup.project')


DEMO_PROJECTS_TEZOS = (
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
    # TODO: demo_jobs
    # TODO: demo_backup
    # TODO: demo_sql
)
DEMO_PROJECTS_EVM = (('', ''),)


class Answers(TypedDict):
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
    crash_reporting: str
    linters: str
    line_length: str


# initialized with default values, changed with survey
DEFAULT_ANSWERS = Answers(
    dipdup_version=__version__.split('.')[0],
    template='demo_dao',
    project_name='dipdup_indexer',
    package='dipdup_indexer',
    version='0.0.1',
    description='My shiny new indexer based on DipDup',
    license='MIT',
    author='John Smith <john_smith@localhost.lan>',
    postgresql_image='postgres:15',
    hasura_image='hasura/graphql-engine:v2.23.0',
    crash_reporting='false',
    linters='default',
    line_length='120',
)


T = TypeVar('T')


def prompt(text: str, default: Any, type_: Type[T], print_default: bool = True) -> T:
    """ Ask user smth with typecast to type, print_default=True print to user what default choise would be used """
    try:
        value: T = cl.prompt(
            text=f'{text} [{default}]: ' if print_default else text,
            default=default,
            type=type_,
            show_default=False,
        )
        print('\n')
        return value
    except cl.Abort:
        cl.echo('\nAborted')
        quit(0)


def choose_one(
    question: str, options: tuple[str, ...], comments: tuple[str, ...], default: int
) -> str:  # default is position of default option in options
    """ Ask user to choose one option with question, list of options and there description(comments) """
    table = tabulate(
        zip(range(len(options)), options, comments),
        colalign=('right', 'left', 'left'),
    )
    cl.secho(f'=> {question}', fg='blue')
    cl.echo(table)

    answer = prompt('Please choose an option', default, type_=int)
    return options[answer]


def fancy_str_prompt(question: str, default: str) -> str:
    """ Blue prompt in dipdup style for str answers """
    cl.secho(f'=> {question} [{default}]: ', fg='blue')
    return prompt('', default, str, print_default=False)


def create_new_project_from_console() -> Answers:
    """ Script running on dipdup new command and will create a new project from console survey """
    answers = copy(DEFAULT_ANSWERS)
    # dict with all new project config

    welcome_text = (
        'Welcome to DipDup! This command will help you to create a new project.\n'
        'You can abort at any time by pressing Ctrl+C. Press Enter to use default value.\n'
        "Let's start with some basic questions."
    )
    cl.secho('\n' + welcome_text + '\n', fg='yellow')

    # Choose new project template
    template_types = ('Tezos', 'EVM', 'Blank')
    template_types_desc = ('Tezos templates', 'EVM templates', 'Brief template to create project from scratch')
    template_type = choose_one(
        'Choose a template: blockchain-specific or blank?', template_types, template_types_desc, default=2
    )

    # list of options can contain folder name of template or folder name of template with description
    # all project templates are in src/dipdup/projects
    template_types_dict: dict[str, tuple[tuple[str, str], ...]] = {
        'Tezos': DEMO_PROJECTS_TEZOS,
        'EVM': DEMO_PROJECTS_EVM,
        'Blank': (('blank', ''),),  # for same typing
    }
    DEMO_PROJECTS_BLANK = 'Blank'
    if template_type == DEMO_PROJECTS_BLANK:
        answers['template'] = template_types_dict[DEMO_PROJECTS_BLANK][0][0]
    else:
        options = tuple(x[0] for x in template_types_dict[template_type])  # FIXME zero EVM templates
        comments = tuple(x[1] for x in template_types_dict[template_type])
        answers['template'] = choose_one(
            'Choose config template depending on the type of your project (DEX, NFT marketplace etc.)\n',
            options,
            comments,
            default=0,
        )

    # define project(folder) and package name for new indexer
    answers['project_name'] = fancy_str_prompt(
        'Enter project name (the name will be used for folder name and package name)', answers['project_name']
    )
    answers['package'] = answers['project_name']  # FIXME validate python package name in question

    # define version for new indexer package
    answers['version'] = fancy_str_prompt('Enter project version', answers['version'])

    # define description for new indexer readme
    answers['description'] = fancy_str_prompt('Enter project description', answers['description'])

    # define author and license for new indexer
    answers['license'] = fancy_str_prompt(
        'Enter project license\n' 'DipDup itself is MIT-licensed.', answers['license']
    )
    answers['author'] = fancy_str_prompt(
        ('Enter project author\n' 'You can add more later in pyproject.toml.'), answers['author']
    )

    cl.secho('\n' + 'Now choose versions of software you want to use.' + '\n', fg='yellow')

    answers['postgresql_image'] = choose_one(
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

    answers['hasura_image'] = choose_one(
        question=(
            'Choose Hasura version\n'
            'Test new releases before using in production; new versions may break compatibility.'
        ),
        options=(
            'hasura/graphql-engine:v2.23.0',
            'hasura/graphql-engine:v2.23.0',
        ),
        comments=(
            'stable',
            'beta',
        ),
        default=0,
    )

    cl.secho('\n' + 'Miscellaneous tunables; leave default values if unsure' + '\n', fg='yellow')

    cl.secho('=> Enable crash reporting?\n' 'It helps us a lot to improve DipDup 🙏 ["y/N"]: ', fg='blue')
    answers['crash_reporting'] = str(prompt('', False, bool, print_default=bool(answers['crash_reporting'])))

    answers['linters'] = choose_one(
        'Choose tools to lint and test your code\n' 'You can always add more later in pyproject.toml.',
        ('default', 'none'),
        ('Classic set: black, isort, ruff, mypy, pytest', 'None'),
        default=0,
    )

    answers['line_length'] = fancy_str_prompt(
        ('Enter maximum line length\n' 'Used by linters.'), default=answers['line_length']
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


def load_project_settings_replay(path: Path) -> Answers:
    if not path.is_file() and path.suffix != '.json':
        raise Exception

    return cast(Answers, orjson.loads(path.read_bytes()))


def render_project_from_template(answers: Answers, force: bool = False) -> None:
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
