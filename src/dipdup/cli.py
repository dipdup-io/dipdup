import asyncio
import atexit
import logging
import os
import signal
import sys
from contextlib import AsyncExitStack
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from functools import wraps
from os.path import dirname
from os.path import exists
from os.path import join
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import cast

import aiohttp
import asyncclick as click
from dotenv import load_dotenv
from tortoise import Tortoise
from tortoise.utils import get_schema_sql

from dipdup import __spec_version__
from dipdup import __version__
from dipdup import spec_reindex_mapping
from dipdup import spec_version_mapping
from dipdup.codegen import DipDupCodeGenerator
from dipdup.config import DipDupConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.config import SentryConfig
from dipdup.dipdup import DipDup
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import DipDupError
from dipdup.exceptions import InitializationRequiredError
from dipdup.exceptions import MigrationRequiredError
from dipdup.exceptions import _tab
from dipdup.exceptions import save_tombstone
from dipdup.hasura import HasuraGateway
from dipdup.models import Index
from dipdup.models import Schema
from dipdup.utils import iter_files
from dipdup.utils.database import generate_schema
from dipdup.utils.database import get_connection
from dipdup.utils.database import tortoise_wrapper
from dipdup.utils.database import wipe_schema

DEFAULT_CONFIG_NAME = 'dipdup.yml'
BAKING_BAD_SENTRY_DSN = 'https://ef33481a853b44e39187bdf2d9eef773@newsentry.baking-bad.org/6'

_logger = logging.getLogger('dipdup.cli')
_is_shutting_down = False


def set_up_logging() -> None:
    root = logging.getLogger()
    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter('%(levelname)-8s %(name)-20s %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # NOTE: Nothing useful there
    logging.getLogger('tortoise').setLevel(logging.WARNING)


def echo(message: str) -> None:
    with suppress(BrokenPipeError):
        click.echo(message)


@dataclass
class CLIContext:
    config_paths: List[str]
    config: DipDupConfig


async def _shutdown() -> None:
    global _is_shutting_down
    if _is_shutting_down:
        return
    _is_shutting_down = True

    _logger.info('Shutting down')
    tasks = filter(lambda t: t != asyncio.current_task(), asyncio.all_tasks())
    list(map(asyncio.Task.cancel, tasks))
    await asyncio.gather(*tasks, return_exceptions=True)


def _print_help(error: Exception, tombstone_path: str) -> None:
    """Prints helpful error message after traceback"""
    help_message = error.format() if isinstance(error, DipDupError) else DipDupError().format()
    help_message += _tab + f'Tombstone saved to `{tombstone_path}`'
    atexit.register(partial(click.echo, help_message, err=True))


def cli_wrapper(fn):
    @wraps(fn)
    async def wrapper(*args, **kwargs) -> None:
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(
            signal.SIGINT,
            lambda: asyncio.ensure_future(_shutdown()),
        )
        try:
            await fn(*args, **kwargs)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        except Exception as e:
            _logger.exception('Unhandled exception caught')
            tombstone_path = save_tombstone(e)
            _print_help(e, tombstone_path)
            raise

    return wrapper


def _sentry_before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if _is_shutting_down:
        return None
    return event


def _init_sentry(config: DipDupConfig) -> None:
    if not config.sentry:
        if not config.advanced.crash_reporting:
            return
        config.sentry = SentryConfig(dsn=BAKING_BAD_SENTRY_DSN)

    if config.sentry.debug:
        level, event_level, attach_stacktrace = logging.DEBUG, logging.WARNING, True
    else:
        level, event_level, attach_stacktrace = logging.INFO, logging.ERROR, False

    # NOTE: Lazy import to speed up startup
    import sentry_sdk
    from sentry_sdk.integrations.aiohttp import AioHttpIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    integrations = [
        AioHttpIntegration(),
        LoggingIntegration(
            level=level,
            event_level=event_level,
        ),
    ]
    sentry_sdk.init(
        dsn=config.sentry.dsn,
        environment=config.sentry.environment,
        server_name=config.sentry.server_name,
        release=config.sentry.release or __version__,
        integrations=integrations,
        attach_stacktrace=attach_stacktrace,
        before_send=_sentry_before_send,
    )
    sentry_sdk.set_tag('dipdup_version', __version__)
    sentry_sdk.set_tag('dipdup_package', config.package)


async def _check_version() -> None:
    if 'rc' in __version__:
        _logger.warning('You are running a pre-release version of DipDup. Please, report any issues to the GitHub repository.')
        _logger.info('Set `skip_version_check` flag in config to hide this message.')
        return

    async with AsyncExitStack() as stack:
        stack.enter_context(suppress(Exception))
        session = await stack.enter_async_context(aiohttp.ClientSession())
        response = await session.get('https://api.github.com/repos/dipdup-net/dipdup-py/releases/latest')
        response_json = await response.json()
        latest_version = response_json['tag_name']

        if __version__ != latest_version:
            _logger.warning('You are running an outdated version of DipDup. Please update to the latest version.')
            _logger.info('Set `skip_version_check` flag in config to hide this message.')


@click.group(context_settings={'max_content_width': 120})
@click.version_option(__version__)
@click.option(
    '--config',
    '-c',
    type=str,
    multiple=True,
    help=f'A path to DipDup project config (default: {DEFAULT_CONFIG_NAME}).',
    default=[DEFAULT_CONFIG_NAME],
)
@click.option(
    '--env-file',
    '-e',
    type=str,
    multiple=True,
    help='A path to .env file containing `KEY=value` strings.',
    default=[],
)
@click.pass_context
@cli_wrapper
async def cli(ctx, config: List[str], env_file: List[str]):
    """Manage and run DipDup indexers.

    Full docs: https://dipdup.net/docs

    Report an issue: https://github.com/dipdup-net/dipdup-py/issues
    """
    # NOTE: Workaround for subcommands
    if '--help' in sys.argv:
        return

    set_up_logging()

    # NOTE: Apply env files before loading config
    for env_path in env_file:
        env_path = join(os.getcwd(), env_path)
        if not exists(env_path):
            raise ConfigurationError(f'env file `{env_path}` does not exist')
        _logger.info('Applying env_file `%s`', env_path)
        load_dotenv(env_path, override=True)

    _config = DipDupConfig.load(config)
    _config.set_up_logging()

    # NOTE: Imports will be loaded later if needed
    _config.initialize(skip_imports=True)
    _init_sentry(_config)

    # NOTE: Fire and forget, do not block instant commands
    if not _config.advanced.skip_version_check:
        asyncio.ensure_future(_check_version())

    # NOTE: Avoid import errors if project package is incomplete
    try:
        await DipDupCodeGenerator(_config, {}).create_package()
    except Exception as e:
        raise InitializationRequiredError('Failed to create a project package.') from e

    # NOTE: Ensure that `spec_version` is valid and supported
    if _config.spec_version not in spec_version_mapping:
        raise ConfigurationError(f'Unknown `spec_version`, correct ones: {", ".join(spec_version_mapping)}')
    if _config.spec_version != __spec_version__:
        reindex = spec_reindex_mapping[__spec_version__]
        raise MigrationRequiredError(_config.spec_version, __spec_version__, reindex)

    ctx.obj = CLIContext(
        config_paths=config,
        config=_config,
    )


@cli.command()
@click.pass_context
@cli_wrapper
async def run(ctx) -> None:
    """Run indexer.

    Execution can be gracefully interrupted with `Ctrl+C` or `SIGTERM` signal.
    """
    config: DipDupConfig = ctx.obj.config
    config.initialize()

    dipdup = DipDup(config)
    await dipdup.run()


@cli.command()
@click.option('--overwrite-types', is_flag=True, help='Regenerate existing types.')
@click.option('--keep-schemas', is_flag=True, help='Do not remove JSONSchemas after generating types.')
@click.pass_context
@cli_wrapper
async def init(ctx, overwrite_types: bool, keep_schemas: bool) -> None:
    """Generate project tree, missing callbacks and types.

    This command is idempotent, meaning it won't overwrite previously generated files unless asked explicitly.
    """
    config: DipDupConfig = ctx.obj.config
    dipdup = DipDup(config)
    await dipdup.init(overwrite_types, keep_schemas)


@cli.command()
@click.pass_context
@cli_wrapper
async def migrate(ctx) -> None:
    """
    Migrate project to the new spec version.

    If you're getting `MigrationRequiredError` after updating DipDup, this command will fix imports and type annotations to match the current `spec_version`. Review and commit changes after running it.
    """
    _logger.info('Project is already at the latest version, no further actions required')


@cli.command()
@click.pass_context
@cli_wrapper
async def status(ctx) -> None:
    """Show the current status of indexes in the database."""
    config: DipDupConfig = ctx.obj.config
    url = config.database.connection_string
    models = f'{config.package}.models'

    table: List[Tuple[str, str, str | int]] = [('name', 'status', 'level')]
    async with tortoise_wrapper(url, models):
        async for index in Index.filter().order_by('name'):
            row = (index.name, index.status.value, index.level)
            table.append(row)

    # NOTE: Lazy import to speed up startup
    from tabulate import tabulate

    echo(tabulate(table, tablefmt='plain'))


@cli.group()
@click.pass_context
@cli_wrapper
async def config(ctx) -> None:
    """Commands to manage DipDup configuration."""
    ...


@config.command(name='export')
@click.option('--unsafe', is_flag=True, help='Resolve environment variables or use default values from config.')
@click.option('--full', is_flag=True, help='Resolve index templates.')
@click.pass_context
@cli_wrapper
async def config_export(ctx, unsafe: bool, full: bool) -> None:
    """
    Print config after resolving all links and, optionally, templates.

    WARNING: Avoid sharing output with 3rd-parties when `--unsafe` flag set - it may contain secrets!
    """
    config = DipDupConfig.load(
        paths=ctx.obj.config.paths,
        environment=unsafe,
    )
    if full:
        config.initialize(skip_imports=True)
    echo(config.dump())


@config.command(name='env')
@click.option('--file', '-f', type=str, default=None, help='Output to file instead of stdout.')
@click.pass_context
@cli_wrapper
async def config_env(ctx, file: Optional[str]) -> None:
    """Dump environment variables used in DipDup config.

    If variable is not set, default value will be used.
    """
    config = DipDupConfig.load(
        paths=ctx.obj.config.paths,
        environment=True,
    )
    content = '\n'.join(f'{k}={v}' for k, v in config.environment.items())
    if file:
        with open(file, 'w') as f:
            f.write(content)
    else:
        echo(content)


@cli.group(help='Hasura integration related commands.')
@click.pass_context
@cli_wrapper
async def hasura(ctx) -> None:
    ...


@hasura.command(name='configure')
@click.option('--force', is_flag=True, help='Proceed even if Hasura is already configured.')
@click.pass_context
@cli_wrapper
async def hasura_configure(ctx, force: bool) -> None:
    """Configure Hasura GraphQL Engine to use with DipDup."""
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
@cli_wrapper
async def schema(ctx) -> None:
    """Manage database schema."""
    ...


@schema.command(name='approve')
@click.pass_context
@cli_wrapper
async def schema_approve(ctx) -> None:
    """Continue to use existing schema after reindexing was triggered."""
    config: DipDupConfig = ctx.obj.config
    url = config.database.connection_string
    models = f'{config.package}.models'

    _logger.info('Approving schema `%s`', url)

    async with tortoise_wrapper(url, models):
        # FIXME: Non-nullable fields
        await Schema.filter(name=config.schema_name).update(
            reindex=None,
            hash='',
        )
        await Index.filter().update(
            config_hash='',
        )

    _logger.info('Schema approved')


@schema.command(name='wipe')
@click.option('--immune', is_flag=True, help='Drop immune tables too.')
@click.option('--force', is_flag=True, help='Skip confirmation prompt.')
@click.pass_context
@cli_wrapper
async def schema_wipe(ctx, immune: bool, force: bool) -> None:
    """
    Drop all database tables, functions and views.

    WARNING: This action is irreversible! All indexed data will be lost!
    """
    config: DipDupConfig = ctx.obj.config
    url = config.database.connection_string
    models = f'{config.package}.models'

    if not force:
        try:
            assert sys.__stdin__.isatty()
            click.confirm(f'You\'re about to wipe schema `{url}`. All indexed data will be irreversibly lost, are you sure?', abort=True)
        except AssertionError:
            click.echo('Not in a TTY, skipping confirmation')
        # FIXME: Can't catch asyncio.CancelledError here
        except click.Abort:
            click.echo('Aborted')
            return

    _logger.info('Wiping schema `%s`', url)

    async with tortoise_wrapper(url, models):
        conn = get_connection()
        if isinstance(config.database, PostgresDatabaseConfig):
            await wipe_schema(
                conn=conn,
                name=config.database.schema_name,
                # NOTE: Don't be confused by the name of `--immune` flag, we want to drop all tables if it's set.
                immune_tables=config.database.immune_tables if not immune else set(),
            )
        else:
            await Tortoise._drop_databases()

    _logger.info('Schema wiped')


@schema.command(name='init')
@click.pass_context
@cli_wrapper
async def schema_init(ctx) -> None:
    """
    Prepare a database for running DipDip.

    This command creates tables based on your models, then executes `sql/on_reindex` to finish preparation - the same things DipDup does when run on a clean database.
    """
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
        await generate_schema(conn, config.database.schema_name)

    _logger.info('Schema initialized')


@schema.command(name='export')
@click.pass_context
@cli_wrapper
async def schema_export(ctx) -> None:
    """Print SQL schema including scripts from `sql/on_reindex`.

    This command may help you debug inconsistency between project models and expected SQL schema.
    """
    config: DipDupConfig = ctx.obj.config
    url = config.database.connection_string
    models = f'{config.package}.models'

    async with tortoise_wrapper(url, models):
        conn = get_connection()
        output = get_schema_sql(conn, False) + '\n'
        dipdup_sql_path = join(dirname(__file__), 'sql', 'on_reindex')
        project_sql_path = join(config.package_path, 'sql', 'on_reindex')

        for sql_path in (dipdup_sql_path, project_sql_path):
            for file in iter_files(sql_path):
                output += file.read() + '\n'

        echo(output)
