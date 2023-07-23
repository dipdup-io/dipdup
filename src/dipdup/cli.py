# NOTE: All imports except the basic ones are very lazy in this module. Let's keep it that way.
import asyncio
import atexit
import logging
import sys
from contextlib import AsyncExitStack
from contextlib import suppress
from copy import copy
from dataclasses import dataclass
from functools import partial
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import TypeVar
from typing import cast

import asyncclick as click

from dipdup import __version__
from dipdup.install import EPILOG
from dipdup.install import WELCOME_ASCII
from dipdup.performance import metrics
from dipdup.report import REPORTS_PATH
from dipdup.report import ReportHeader
from dipdup.report import save_report
from dipdup.sys import set_up_process

_click_wrap_text = click.formatting.wrap_text


def _wrap_text(text: str, *a: Any, **kw: Any) -> str:
    # NOTE: WELCOME_ASCII and EPILOG
    if text.startswith(('    ')):
        return text
    if text.startswith(('\0\n')):
        return text[2:]
    return _click_wrap_text(text, *a, **kw)


click.formatting.wrap_text = _wrap_text

ROOT_CONFIG = 'dipdup.yaml'
CONFIG_RE = r'dipdup.*\.ya?ml'

# NOTE: Do not try to load config for these commands as they don't need it
NO_CONFIG_CMDS = {
    'new',
    'install',
    'uninstall',
    'update',
}
# NOTE: Our signal handler conflicts with Click's one in prompt mode
NO_SIGNALS_CMDS = {
    *NO_CONFIG_CMDS,
    None,
    'schema',
    'wipe',
}

if TYPE_CHECKING:
    from dipdup.config import DipDupConfig

_logger = logging.getLogger(__name__)


def echo(message: str) -> None:
    with suppress(BrokenPipeError):
        click.echo(message)


def _print_help(error: Exception) -> None:
    """Prints a helpful error message after the traceback"""
    from dipdup.exceptions import Error

    def _print() -> None:
        if isinstance(error, Error):
            click.echo(error.help(), err=True)
        else:
            click.echo(Error.default_help())

    atexit.register(_print)


def _print_report(name: str) -> None:
    atexit.register(partial(click.echo, f'Report saved; run `dipdup report show {name}` to view it'))


WrappedCommandT = TypeVar('WrappedCommandT', bound=Callable[..., Awaitable[None]])


@dataclass
class CLIContext:
    config_paths: list[str]
    config: 'DipDupConfig'


def _cli_wrapper(fn: WrappedCommandT) -> WrappedCommandT:
    @wraps(fn)
    async def wrapper(ctx: click.Context, *args: Any, **kwargs: Any) -> None:
        signals = ctx.invoked_subcommand not in NO_SIGNALS_CMDS
        set_up_process(signals)

        try:
            await fn(ctx, *args, **kwargs)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        except Exception as e:
            package = ctx.obj.config.package if ctx.obj else 'unknown'
            report_id = save_report(package, e)
            _print_report(report_id)
            _print_help(e)

            if metrics:
                raise e
            sys.exit(1)

        if fn.__name__ == 'run':
            package = ctx.obj.config.package
            save_report(package, None)

    return cast(WrappedCommandT, wrapper)


async def _check_version() -> None:
    if 'rc' in __version__ or 'b' in __version__:
        _logger.warning(
            'You are running a pre-release version of DipDup. Please, report any issues to the GitHub repository.'
        )
        _logger.info('Set `skip_version_check` flag in config to hide this message.')
        return

    import aiohttp

    async with AsyncExitStack() as stack:
        stack.enter_context(suppress(Exception))
        session = await stack.enter_async_context(aiohttp.ClientSession())
        response = await session.get('https://api.github.com/repos/dipdup-io/dipdup/releases/latest')
        response_json = await response.json()
        latest_version = response_json['tag_name']

        if __version__ != latest_version:
            _logger.warning('You are running an outdated version of DipDup. Please run `dipdup update`.')
            _logger.info('Set `skip_version_check` flag in config to hide this message.')


@click.group(
    context_settings={'max_content_width': 120},
    help=WELCOME_ASCII,
    epilog=EPILOG,
)
@click.version_option(__version__)
@click.option(
    '--config',
    '-c',
    type=str,
    multiple=True,
    help='A path to DipDup project config.',
    default=[ROOT_CONFIG],
    metavar='PATH',
)
@click.option(
    '--env-file',
    '-e',
    type=str,
    multiple=True,
    help='A path to .env file containing `KEY=value` strings.',
    default=[],
    metavar='PATH',
)
@click.pass_context
@_cli_wrapper
async def cli(ctx: click.Context, config: list[str], env_file: list[str]) -> None:
    # NOTE: Workaround for help pages. First argument check is for the test runner.
    args = sys.argv[1:] if sys.argv else ['--help']
    if '--help' in args or args in (['config'], ['hasura'], ['schema']) or args[0] in ('self', 'report'):
        return

    from dotenv import load_dotenv

    from dipdup.exceptions import ConfigurationError
    from dipdup.sys import set_up_logging

    set_up_logging()

    env_file_paths = [Path(file) for file in env_file]
    config_paths = [Path(file) for file in config]

    # NOTE: Apply env files before loading config
    for env_path in env_file_paths:
        if not env_path.is_file():
            raise ConfigurationError(f'env file `{env_path}` does not exist')
        _logger.info('Applying env_file `%s`', env_path)
        load_dotenv(env_path, override=True)

    # NOTE: These commands need no other preparations
    if ctx.invoked_subcommand in NO_CONFIG_CMDS:
        logging.getLogger('dipdup').setLevel(logging.INFO)
        return

    from dipdup import env
    from dipdup.config import DipDupConfig
    from dipdup.exceptions import InitializationRequiredError
    from dipdup.package import DipDupPackage
    from dipdup.sentry import init_sentry

    _config = DipDupConfig.load(config_paths)
    _config.set_up_logging()

    init_sentry(_config)

    # NOTE: Imports will be loaded later if needed
    _config.initialize()

    # NOTE: Fire and forget, do not block instant commands
    if not any((_config.advanced.skip_version_check, env.TEST, env.CI)):
        asyncio.ensure_future(_check_version())

    try:
        # NOTE: Avoid early import errors if project package is incomplete.
        # NOTE: `ConfigurationError` will be raised with more details.
        DipDupPackage(_config.package_path).create()
    except Exception as e:
        if ctx.invoked_subcommand != 'init':
            raise InitializationRequiredError(f'Failed to create a project package: {e}') from e

    ctx.obj = CLIContext(
        config_paths=config,
        config=_config,
    )


@cli.command()
@click.pass_context
@_cli_wrapper
async def run(ctx: click.Context) -> None:
    """Run indexer.

    Execution can be gracefully interrupted with `Ctrl+C` or `SIGINT` signal.
    """
    from dipdup.config import DipDupConfig
    from dipdup.dipdup import DipDup

    config: DipDupConfig = ctx.obj.config
    config.initialize()

    dipdup = DipDup(config)
    await dipdup.run()


@cli.command()
@click.option('--force', '-f', is_flag=True, help='Regenerate existing types and ABIs.')
@click.pass_context
@_cli_wrapper
async def init(ctx: click.Context, force: bool) -> None:
    """Generate project tree, callbacks and types.

    This command is idempotent, meaning it won't overwrite previously generated files unless asked explicitly.
    """
    from dipdup.dipdup import DipDup

    config: DipDupConfig = ctx.obj.config
    dipdup = DipDup(config)
    await dipdup.init(force)


@cli.command()
@click.pass_context
@_cli_wrapper
async def migrate(ctx: click.Context) -> None:
    """
    Migrate project to the new spec version.

    If you're getting `MigrationRequiredError` after updating DipDup, this command will fix imports and type annotations to match the current `spec_version`. Review and commit changes after running it.
    """
    _logger.info('Project is already at the latest version, no further actions required')


@cli.group()
@click.pass_context
@_cli_wrapper
async def config(ctx: click.Context) -> None:
    """Commands to manage DipDup configuration."""
    pass


@config.command(name='export')
@click.option('--unsafe', is_flag=True, help='Resolve environment variables or use default values from config.')
@click.option('--full', is_flag=True, help='Resolve index templates.')
@click.pass_context
@_cli_wrapper
async def config_export(ctx: click.Context, unsafe: bool, full: bool) -> None:
    """
    Print config after resolving all links and, optionally, templates.

    WARNING: Avoid sharing output with 3rd-parties when `--unsafe` flag set - it may contain secrets!
    """
    from dipdup.config import DipDupConfig

    config = DipDupConfig.load(
        paths=ctx.obj.config.paths,
        environment=unsafe,
    )
    if full:
        config.initialize()
    echo(config.dump())


@config.command(name='env')
@click.option('--output', '-o', type=str, default=None, help='Output to file instead of stdout.')
@click.pass_context
@_cli_wrapper
async def config_env(ctx: click.Context, output: str | None) -> None:
    """Dump environment variables used in DipDup config.

    If variable is not set, default value will be used.
    """
    from dipdup.config import DipDupConfig

    config = DipDupConfig.load(
        paths=ctx.obj.config.paths,
        environment=True,
    )
    content = '\n'.join(f'{k}={v}' for k, v in sorted(config.environment.items()))
    if output:
        Path(output).write_text(content)
    else:
        echo(content)


@cli.group(help='Commands related to Hasura integration.')
@click.pass_context
@_cli_wrapper
async def hasura(ctx: click.Context) -> None:
    pass


@hasura.command(name='configure')
@click.option('--force', is_flag=True, help='Proceed even if Hasura is already configured.')
@click.pass_context
@_cli_wrapper
async def hasura_configure(ctx: click.Context, force: bool) -> None:
    """Configure Hasura GraphQL Engine to use with DipDup."""
    from dipdup.config import DipDupConfig
    from dipdup.config import PostgresDatabaseConfig
    from dipdup.database import tortoise_wrapper
    from dipdup.exceptions import ConfigurationError
    from dipdup.hasura import HasuraGateway

    config: DipDupConfig = ctx.obj.config
    if not config.hasura:
        raise ConfigurationError('`hasura` config section is empty')
    hasura_gateway = HasuraGateway(
        package=config.package,
        hasura_config=config.hasura,
        database_config=cast(PostgresDatabaseConfig, config.database),
    )

    async with AsyncExitStack() as stack:
        await stack.enter_async_context(
            tortoise_wrapper(
                url=config.database.connection_string,
                models=config.package,
                timeout=config.database.connection_timeout,
            )
        )
        await stack.enter_async_context(hasura_gateway)

        await hasura_gateway.configure(force)


@cli.group()
@click.pass_context
@_cli_wrapper
async def schema(ctx: click.Context) -> None:
    """Commands to manage database schema."""
    pass


@schema.command(name='approve')
@click.pass_context
@_cli_wrapper
async def schema_approve(ctx: click.Context) -> None:
    """Continue to use existing schema after reindexing was triggered."""

    from dipdup.config import DipDupConfig
    from dipdup.database import tortoise_wrapper
    from dipdup.models import Index
    from dipdup.models import Schema

    config: DipDupConfig = ctx.obj.config
    url = config.database.connection_string
    models = f'{config.package}.models'

    _logger.info('Approving schema `%s`', url)

    async with tortoise_wrapper(
        url=url,
        models=models,
        timeout=config.database.connection_timeout,
        decimal_precision=config.advanced.decimal_precision,
    ):
        await Schema.filter(name=config.schema_name).update(
            reindex=None,
            hash=None,
        )
        await Index.filter().update(
            config_hash=None,
        )

    _logger.info('Schema approved')


@schema.command(name='wipe')
@click.option('--immune', is_flag=True, help='Drop immune tables too.')
@click.option('--force', is_flag=True, help='Skip confirmation prompt.')
@click.pass_context
@_cli_wrapper
async def schema_wipe(ctx: click.Context, immune: bool, force: bool) -> None:
    """
    Drop all database tables, functions and views.

    WARNING: This action is irreversible! All indexed data will be lost!
    """
    from dipdup.config import SqliteDatabaseConfig
    from dipdup.exceptions import ConfigurationError

    config: DipDupConfig = ctx.obj.config
    url = config.database.connection_string
    models = f'{config.package}.models'

    # NOTE: Don't be confused by the name of `--immune` flag, we want to drop all tables if it's set.
    immune_tables = set() if immune else config.database.immune_tables | {'dipdup_meta'}

    if isinstance(config.database, SqliteDatabaseConfig) and immune_tables:
        message = 'Support for immune tables in SQLite is experimental and requires `advanced.unsafe_sqlite` flag set'
        if config.advanced.unsafe_sqlite:
            _logger.warning(message)
        else:
            raise ConfigurationError(message)

    if not force:
        try:
            assert sys.__stdin__.isatty()
            click.confirm(
                f"You're about to wipe schema `{url}`. All indexed data will be irreversibly lost, are you sure?",
                abort=True,
            )
        except AssertionError:
            click.echo('Not in a TTY, skipping confirmation')
        except click.Abort:
            click.echo('\nAborted')
            quit(0)

    _logger.info('Wiping schema `%s`', url)

    from dipdup.database import get_connection
    from dipdup.database import tortoise_wrapper
    from dipdup.database import wipe_schema

    async with tortoise_wrapper(
        url=url,
        models=models,
        timeout=config.database.connection_timeout,
        decimal_precision=config.advanced.decimal_precision,
    ):
        conn = get_connection()
        await wipe_schema(
            conn=conn,
            schema_name=config.database.schema_name,
            immune_tables=immune_tables,
        )

    _logger.info('Schema wiped')


@schema.command(name='init')
@click.pass_context
@_cli_wrapper
async def schema_init(ctx: click.Context) -> None:
    """
    Prepare a database for running DipDip.

    This command creates tables based on your models, then executes `sql/on_reindex` to finish preparation - the same things DipDup does when run on a clean database.
    """
    from dipdup.database import generate_schema
    from dipdup.database import get_connection
    from dipdup.dipdup import DipDup

    config: DipDupConfig = ctx.obj.config
    url = config.database.connection_string
    dipdup = DipDup(config)

    _logger.info('Initializing schema `%s`', url)

    async with AsyncExitStack() as stack:
        await dipdup._set_up_database(stack)
        await dipdup._set_up_hooks(set())
        await dipdup._create_datasources()
        await dipdup._initialize_schema()

        # NOTE: It's not necessary a reindex, but it's safe to execute built-in scripts to (re)create views.
        conn = get_connection()
        await generate_schema(
            conn,
            config.database.schema_name,
        )

    _logger.info('Schema initialized')


@schema.command(name='export')
@click.pass_context
@_cli_wrapper
async def schema_export(ctx: click.Context) -> None:
    """Print SQL schema including scripts from `sql/on_reindex`.

    This command may help you debug inconsistency between project models and expected SQL schema.
    """

    from tortoise.utils import get_schema_sql

    from dipdup import env
    from dipdup.database import get_connection
    from dipdup.database import tortoise_wrapper
    from dipdup.utils import iter_files

    config: DipDupConfig = ctx.obj.config
    url = config.database.connection_string
    models = f'{config.package}.models'
    package_path = env.get_package_path(config.package)

    async with tortoise_wrapper(
        url=url,
        models=models,
        timeout=config.database.connection_timeout,
        decimal_precision=config.advanced.decimal_precision,
    ):
        conn = get_connection()
        output = get_schema_sql(conn, False) + '\n'
        dipdup_sql_path = Path(__file__).parent / 'sql' / 'on_reindex'
        project_sql_path = package_path / 'sql' / 'on_reindex'

        for sql_path in (dipdup_sql_path, project_sql_path):
            for file in iter_files(sql_path):
                output += file.read() + '\n'

        echo(output)


@cli.command()
@click.pass_context
@click.option('--quiet', '-q', is_flag=True, help='Use default values for all prompts.')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing files.')
@click.option(
    '--replay',
    '-r',
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help='Replay a previously saved state.',
)
@_cli_wrapper
async def new(
    ctx: click.Context,
    quiet: bool,
    force: bool,
    replay: Path | None,
) -> None:
    """Create a new project interactively."""
    from dipdup.project import DEFAULT_ANSWERS
    from dipdup.project import answers_from_replay
    from dipdup.project import answers_from_terminal
    from dipdup.project import render_project

    if quiet:
        answers = copy(DEFAULT_ANSWERS)
    elif replay:
        answers = answers_from_replay(replay)
    else:
        answers = answers_from_terminal()
    render_project(answers, force)


@cli.group()
@click.pass_context
@_cli_wrapper
async def self(ctx: click.Context) -> None:
    """Commands to manage local DipDup installation."""
    pass


@self.command(name='install')
@click.pass_context
@click.option('--quiet', '-q', is_flag=True, help='Use default values for all prompts.')
@click.option('--force', '-f', is_flag=True, help='Force reinstall.')
@click.option('--version', '-v', default=None, help='Install DipDup from a specific version.')
@click.option('--ref', '-r', default=None, help='Install DipDup from a specific git ref.')
@click.option('--path', '-p', default=None, help='Install DipDup from a local path.')
@_cli_wrapper
async def self_install(
    ctx: click.Context,
    quiet: bool,
    force: bool,
    version: str | None,
    ref: str | None,
    path: str | None,
) -> None:
    """Install DipDup for the current user."""
    import dipdup.install

    dipdup.install.install(quiet, force, version, ref, path)


@self.command(name='uninstall')
@click.pass_context
@click.option('--quiet', '-q', is_flag=True, help='Use default values for all prompts.')
@_cli_wrapper
async def self_uninstall(
    ctx: click.Context,
    quiet: bool,
) -> None:
    """Uninstall DipDup for the current user."""
    import dipdup.install

    dipdup.install.uninstall(quiet)


@self.command(name='update')
@click.pass_context
@click.option('--quiet', '-q', is_flag=True, help='Use default values for all prompts.')
@click.option('--force', '-f', is_flag=True, help='Force reinstall.')
@_cli_wrapper
async def self_update(
    ctx: click.Context,
    quiet: bool,
    force: bool,
) -> None:
    """Update DipDup for the current user."""
    import dipdup.install

    dipdup.install.install(quiet, force, None, None, None)


@cli.group(invoke_without_command=True)
@click.pass_context
@_cli_wrapper
async def report(ctx: click.Context) -> None:
    """List and manage reports."""
    if ctx.invoked_subcommand:
        return

    header = tuple(ReportHeader.__annotations__.keys())
    rows = []
    for path in REPORTS_PATH.iterdir():
        if path.suffix not in ('.yml', '.yaml'):
            continue

        from ruamel.yaml import YAML

        event = YAML(typ='base').load(path)
        row = [event.get(key, 'none')[:80] for key in header]
        rows.append(row)

    rows.sort(key=lambda row: str(row[3]))

    from tabulate import tabulate

    echo(tabulate(rows, headers=header))


@report.command(name='show')
@click.pass_context
@click.argument('id', type=str)
@_cli_wrapper
async def report_show(ctx: click.Context, id: str) -> None:
    path = REPORTS_PATH / f'{id}.yaml'
    if not path.exists():
        echo('No such report')
        return
    print(path.read_text())


@report.command(name='rm')
@click.pass_context
@click.argument('id', type=str, required=False)
@click.option('--all', '-a', is_flag=True, help='Remove all reports.')
@_cli_wrapper
async def report_rm(ctx: click.Context, id: str | None, all: bool) -> None:
    if all and id:
        echo('Please specify either name or --all')
        return
    if all:
        path = REPORTS_PATH
        for file in path.iterdir():
            file.unlink()
        return

    path = REPORTS_PATH / f'{id}.yaml'
    if not path.exists():
        echo('No such report')
        return
    path.unlink()


@cli.group()
@click.pass_context
@_cli_wrapper
async def package(ctx: click.Context) -> None:
    """Inspect and manage project package."""
    pass


@package.command(name='tree')
@click.pass_context
@_cli_wrapper
async def package_tree(ctx: click.Context) -> None:
    from dipdup.package import DipDupPackage
    from dipdup.package import draw_package_tree

    config: DipDupConfig = ctx.obj.config
    package = DipDupPackage(config.package_path)
    package.create()
    tree = package.discover()
    echo(f'{package.name} [{package.root.relative_to(Path.cwd())}]')
    for line in draw_package_tree(package.root, tree):
        echo(line)
