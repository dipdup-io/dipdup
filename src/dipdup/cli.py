# NOTE: All imports except the basic ones are very lazy in this module. Let's keep it that way.
import asyncio
import atexit
import logging
import sys
from collections.abc import Awaitable
from collections.abc import Callable
from contextlib import AsyncExitStack
from contextlib import suppress
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar
from typing import cast

import asyncclick as click

from dipdup import __version__
from dipdup import env
from dipdup.install import EPILOG
from dipdup.install import WELCOME_ASCII
from dipdup.report import REPORTS_PATH
from dipdup.report import ReportHeader
from dipdup.report import cleanup_reports
from dipdup.report import get_reports
from dipdup.report import save_report
from dipdup.sys import fire_and_forget
from dipdup.sys import set_up_process

if TYPE_CHECKING:
    from dipdup.config import DipDupConfig


_click_wrap_text = click.formatting.wrap_text


def _wrap_text(text: str, *a: Any, **kw: Any) -> str:
    # NOTE: WELCOME_ASCII and EPILOG
    if text.startswith('    '):
        return text
    if text.startswith('\0\n'):
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


_logger = logging.getLogger(__name__)


def echo(message: str, err: bool = False, **styles: Any) -> None:
    with suppress(BrokenPipeError):
        click.secho(message, err=err, **styles)


def big_yellow_echo(message: str) -> None:
    echo(f'\n{message}\n', fg='yellow')


def green_echo(message: str) -> None:
    echo(message, fg='green')


def red_echo(message: str) -> None:
    echo(message, err=True, fg='red')


def _print_help_atexit(error: Exception, report_id: str) -> None:
    """Prints a helpful error message after the traceback"""
    from dipdup.exceptions import Error

    def _print() -> None:
        if isinstance(error, Error):
            echo(error.help(), err=True)
        else:
            echo(Error.default_help(), err=True)

        echo(f'Report saved; run `dipdup report show {report_id}` to view it', err=True)

    atexit.register(_print)


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
            _print_help_atexit(e, report_id)
            raise e

        # NOTE: If indexing was interrupted by signal, save report with just performance metrics.
        if fn.__name__ == 'run':
            package = ctx.obj.config.package
            save_report(package, None)

    return cast(WrappedCommandT, wrapper)


async def _check_version() -> None:
    if '+editable' in __version__:
        return
    if '-rc' in __version__:
        _logger.warning(
            'You are running a pre-release version of DipDup. Please, report any issues to the GitHub repository.'
        )
        _logger.info('Set `advanced.skip_version_check` flag in config to hide this message.')
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


def _skip_cli_group() -> bool:
    # NOTE: Workaround for help pages. First argument check is for the test runner.
    args = sys.argv[1:] if sys.argv else ['--help']
    is_help = '--help' in args
    is_empty_group = args in (
        ['config'],
        ['hasura'],
        ['schema'],
    )
    # NOTE: Simple helpers that don't use any of our cli boilerplate
    is_script = args[0] in (
        'self',
        'report',
    )
    if not (is_help or is_empty_group or is_script):
        _logger.debug('Skipping cli group')
        return False
    return True


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
    envvar='DIPDUP_CONFIG',
)
@click.option(
    '--env-file',
    '-e',
    type=str,
    multiple=True,
    help='A path to .env file containing `KEY=value` strings.',
    default=[],
    metavar='PATH',
    envvar='DIPDUP_ENV_FILE',
)
@click.pass_context
@_cli_wrapper
async def cli(ctx: click.Context, config: list[str], env_file: list[str]) -> None:
    if _skip_cli_group():
        return

    # NOTE: https://github.com/python/cpython/issues/95778
    # NOTE: Method is not available in early Python 3.11
    try:
        sys.set_int_max_str_digits(0)
    except AttributeError:
        _logger.warning("You're running an outdated Python 3.11 release; consider upgrading")

    from dotenv import load_dotenv

    from dipdup.exceptions import ConfigurationError
    from dipdup.sys import set_up_logging

    set_up_logging()

    env_file_paths = [Path(file) for file in env_file]
    config_paths = [Path(file) for file in config]

    # NOTE: Apply env files before loading the config
    for env_path in env_file_paths:
        if not env_path.is_file():
            raise ConfigurationError(f'env file `{env_path}` does not exist')
        _logger.info('Applying env_file `%s`', env_path)
        load_dotenv(env_path, override=True)

    # NOTE: These commands need no other preparations
    if ctx.invoked_subcommand in NO_CONFIG_CMDS:
        logging.getLogger('dipdup').setLevel(logging.INFO)
        return

    from dipdup.config import DipDupConfig
    from dipdup.exceptions import InitializationRequiredError
    from dipdup.package import DipDupPackage

    _config = DipDupConfig.load(config_paths)
    _config.set_up_logging()

    if _config.sentry:
        from dipdup.sentry import init_sentry

        init_sentry(_config.sentry, _config.package)

    # NOTE: Imports will be loaded later if needed
    _config.initialize()

    # NOTE: Fire and forget, do not block instant commands
    if not any((_config.advanced.skip_version_check, env.TEST, env.CI, env.NO_VERSION_CHECK)):
        fire_and_forget(_check_version())

    try:
        # NOTE: Avoid early import errors if project package is incomplete.
        # NOTE: `ConfigurationError` will be raised later with more details.
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
    """Run the indexer.

    Execution can be gracefully interrupted with `Ctrl+C` or `SIGINT` signal.
    """
    from dipdup.dipdup import DipDup

    config: DipDupConfig = ctx.obj.config
    config.initialize()

    dipdup = DipDup(config)
    await dipdup.run()


@cli.command()
@click.option('--force', '-f', is_flag=True, help='Overwrite existing types and ABIs.')
@click.option('--base', '-b', is_flag=True, help='Include template base: pyproject.toml, Dockerfile, etc.')
@click.argument(
    'include',
    type=str,
    nargs=-1,
    metavar='PATH',
)
@click.pass_context
@_cli_wrapper
async def init(
    ctx: click.Context,
    force: bool,
    base: bool,
    include: list[str],
) -> None:
    """Generate project tree, typeclasses and callback stubs.

    This command is idempotent, meaning it won't overwrite previously generated files unless asked explicitly.
    """
    from dipdup.dipdup import DipDup

    config: DipDupConfig = ctx.obj.config
    dipdup = DipDup(config)

    await dipdup.init(
        force=force,
        base=base or bool(include),
        include=set(include),
    )


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
@click.option('--unsafe', is_flag=True, help='Resolve environment variables or use default values from the config.')
@click.option('--full', '-f', is_flag=True, help='Resolve index templates.')
@click.pass_context
@_cli_wrapper
async def config_export(ctx: click.Context, unsafe: bool, full: bool) -> None:
    """
    Print config after resolving all links and, optionally, templates.

    WARNING: Avoid sharing output with 3rd-parties when `--unsafe` flag set - it may contain secrets!
    """
    from dipdup.config import DipDupConfig

    config = DipDupConfig.load(
        paths=ctx.obj.config._paths,
        environment=unsafe,
    )
    if full:
        config.initialize()
    echo(config.dump())


@config.command(name='env')
@click.option('--output', '-o', type=str, default=None, help='Output to file instead of stdout.')
@click.option('--unsafe', is_flag=True, help='Resolve environment variables or use default values from the config.')
@click.option('--compose', '-c', is_flag=True, help='Output in docker-compose format.')
@click.option('--internal', '-i', is_flag=True, help='Include internal variables.')
@click.pass_context
@_cli_wrapper
async def config_env(
    ctx: click.Context,
    output: str | None,
    unsafe: bool,
    compose: bool,
    internal: bool,
) -> None:
    """Dump environment variables used in DipDup config.

    If variable is not set, default value will be used.
    """
    from dipdup.yaml import DipDupYAMLConfig

    _, environment = DipDupYAMLConfig.load(
        paths=ctx.obj.config._paths,
        environment=unsafe,
    )
    if internal:
        environment.update(env.dump())
    if compose:
        content = 'services:\n  dipdup:\n    environment:\n'
        _tab = ' ' * 6
        for k, v in sorted(environment.items()):
            line = f'{_tab}- {k}=' + '${' + k
            if v is not None:
                line += ':-' + v + '}'
            else:
                line += '}'

            content += line + '\n'
    else:
        content = '\n'.join(f'{k}={v}' for k, v in sorted(environment.items()))
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
@click.option('--force', '-f', is_flag=True, help='Proceed even if Hasura is already configured.')
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
@click.option('--immune', '-i', is_flag=True, help='Drop immune tables too.')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt.')
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
    immune_tables = set() if immune else config.database.immune_tables

    if isinstance(config.database, SqliteDatabaseConfig):
        message = 'Support for immune tables in SQLite is experimental and requires `advanced.unsafe_sqlite` flag set'
        if config.advanced.unsafe_sqlite:
            immune_tables.add('dipdup_meta')
            _logger.warning(message)
        elif immune_tables:
            raise ConfigurationError(message)
    else:
        immune_tables.add('dipdup_meta')

    if not force:
        try:
            assert sys.__stdin__.isatty()
            click.confirm(
                f"You're about to wipe schema `{url}`. All indexed data will be irreversibly lost, are you sure?",
                abort=True,
            )
        except AssertionError:
            echo('Not in a TTY, skipping confirmation')
        except click.Abort:
            echo('\nAborted')
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
        unsafe_sqlite=config.advanced.unsafe_sqlite,
    ):
        conn = get_connection()
        await wipe_schema(
            conn=conn,
            schema_name=(
                config.database.path
                if isinstance(config.database, SqliteDatabaseConfig)
                else config.database.schema_name
            ),
            immune_tables=immune_tables,
        )

    _logger.info('Schema wiped')


@schema.command(name='init')
@click.pass_context
@_cli_wrapper
async def schema_init(ctx: click.Context) -> None:
    """
    Prepare database schema for running DipDup.

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
        await dipdup._set_up_hooks()
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
    help='Use values from a replay file.',
)
@_cli_wrapper
async def new(
    ctx: click.Context,
    quiet: bool,
    force: bool,
    replay: Path | None,
) -> None:
    """Create a new project interactively."""
    import os

    from dipdup.config import DipDupConfig
    from dipdup.project import answers_from_replay
    from dipdup.project import answers_from_terminal
    from dipdup.project import get_default_answers
    from dipdup.project import render_project

    if quiet:
        answers = get_default_answers()
    elif replay:
        answers = answers_from_replay(replay)
    else:
        answers = answers_from_terminal()

    _logger.info('Rendering project')
    render_project(answers, force)

    _logger.info('Initializing project')
    config = DipDupConfig.load([Path(answers['package'])])
    config.initialize()
    ctx.obj = CLIContext(
        config_paths=[Path(answers['package']).joinpath(ROOT_CONFIG).as_posix()],
        config=config,
    )
    # NOTE: datamodel-codegen fails otherwise
    os.chdir(answers['package'])
    await ctx.invoke(init, base=True, force=force)

    green_echo('Project created successfully!')
    green_echo(f"Enter `{answers['package']}` directory and see README.md for the next steps.")


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
@click.option('--version', '-v', default=None, help='Install DipDup from specific version.')
@click.option('--ref', '-r', default=None, help='Install DipDup from specific git ref.')
@click.option('--path', '-p', default=None, help='Install DipDup from local path.')
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
    import dipdup.project

    replay = dipdup.project.get_package_answers()
    dipdup.install.install(
        quiet=quiet,
        force=force,
        version=version,
        ref=ref,
        path=path,
        with_pdm=replay is not None and replay['package_manager'] == 'pdm',
        with_poetry=replay is not None and replay['package_manager'] == 'poetry',
    )


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
    import dipdup.project

    replay = dipdup.project.get_package_answers()
    dipdup.install.install(
        quiet=quiet,
        force=force,
        version=None,
        ref=None,
        path=None,
        with_pdm=replay is not None and replay['package_manager'] == 'pdm',
        with_poetry=replay is not None and replay['package_manager'] == 'poetry',
    )


@self.command(name='env', hidden=True)
@click.pass_context
@_cli_wrapper
async def self_env(ctx: click.Context) -> None:
    import dipdup.install

    env = dipdup.install.DipDupEnvironment()
    env.refresh()
    env.print()


@cli.group()
@click.pass_context
@_cli_wrapper
async def report(ctx: click.Context) -> None:
    """Manage crash and performance reports."""
    cleanup_reports()


@report.command(name='ls')
@click.pass_context
@_cli_wrapper
async def report_ls(ctx: click.Context) -> None:
    """List reports."""
    from ruamel.yaml import YAML
    from tabulate import tabulate

    yaml = YAML(typ='base')
    header = tuple(ReportHeader.__annotations__.keys())
    rows = []
    for path in get_reports():
        event = yaml.load(path)
        row = [event.get(key, 'none')[:80] for key in header]
        rows.append(row)

    rows.sort(key=lambda row: str(row[3]))
    echo(tabulate(rows, headers=header))


@report.command(name='show')
@click.pass_context
@click.argument('id', type=str)
@_cli_wrapper
async def report_show(ctx: click.Context, id: str) -> None:
    """Show report."""
    path = REPORTS_PATH / f'{id}.yaml'
    if not path.exists():
        echo('No such report')
        return
    echo(path.read_text())


@report.command(name='rm')
@click.pass_context
@click.argument('id', type=str, required=False)
@click.option('--all', '-a', is_flag=True, help='Remove all reports.')
@_cli_wrapper
async def report_rm(ctx: click.Context, id: str | None, all: bool) -> None:
    """Remove report(s)."""
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
    """Draw package tree."""
    from dipdup.package import DipDupPackage
    from dipdup.package import draw_package_tree

    config: DipDupConfig = ctx.obj.config
    package = DipDupPackage(config.package_path)
    package.create()
    tree = package.tree()
    echo(f'{package.name} [{package.root.relative_to(Path.cwd())}]')
    for line in draw_package_tree(package.root, tree):
        echo(line)
