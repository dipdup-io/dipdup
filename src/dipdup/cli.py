import asyncio
import atexit
import logging
import os
import signal
import subprocess
import sys
from contextlib import AsyncExitStack
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from functools import wraps
from os.path import dirname
from os.path import exists
from os.path import join
from typing import List
from typing import cast

import asyncclick as click
import sentry_sdk
from dotenv import load_dotenv
from fcache.cache import FileCache  # type: ignore
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from tabulate import tabulate
from tortoise import Tortoise
from tortoise.transactions import get_connection
from tortoise.utils import get_schema_sql

from dipdup import __spec_version__
from dipdup import __version__
from dipdup import spec_reindex_mapping
from dipdup import spec_version_mapping
from dipdup.codegen import DipDupCodeGenerator
from dipdup.config import DipDupConfig
from dipdup.config import LoggingConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.dipdup import DipDup
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import DipDupError
from dipdup.exceptions import InitializationRequiredError
from dipdup.exceptions import MigrationRequiredError
from dipdup.hasura import HasuraGateway
from dipdup.migrations import DipDupMigrationManager
from dipdup.models import Index
from dipdup.models import Schema
from dipdup.utils import iter_files
from dipdup.utils.database import execute_sql_scripts
from dipdup.utils.database import set_decimal_context
from dipdup.utils.database import tortoise_wrapper
from dipdup.utils.database import wipe_schema

_logger = logging.getLogger('dipdup.cli')
_is_shutting_down = False


def echo(message: str) -> None:
    with suppress(BrokenPipeError):
        click.echo(message)


@dataclass
class CLIContext:
    config_paths: List[str]
    config: DipDupConfig
    logging_config: LoggingConfig


async def shutdown() -> None:
    global _is_shutting_down
    if _is_shutting_down:
        return
    _is_shutting_down = True

    _logger.info('Shutting down')
    tasks = filter(lambda t: t != asyncio.current_task(), asyncio.all_tasks())
    list(map(asyncio.Task.cancel, tasks))
    await asyncio.gather(*tasks, return_exceptions=True)


def cli_wrapper(fn):
    @wraps(fn)
    async def wrapper(*args, **kwargs) -> None:
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.ensure_future(shutdown()))
        try:
            await fn(*args, **kwargs)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        except Exception as e:
            help_message = e.format() if isinstance(e, DipDupError) else DipDupError().format()
            atexit.register(partial(click.echo, help_message, err=True))
            raise

    return wrapper


def _sentry_before_send(event, _):
    if _is_shutting_down:
        return None
    return event


def init_sentry(config: DipDupConfig) -> None:
    if not config.sentry:
        return
    if config.sentry.debug:
        level, event_level, attach_stacktrace = logging.DEBUG, logging.WARNING, True
    else:
        level, event_level, attach_stacktrace = logging.INFO, logging.ERROR, False

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
        integrations=integrations,
        release=__version__,
        attach_stacktrace=attach_stacktrace,
        before_send=_sentry_before_send,
    )


@click.group(help='Docs: https://docs.dipdup.net', context_settings={'max_content_width': 120})
@click.version_option(__version__)
@click.option('--config', '-c', type=str, multiple=True, help='Path to dipdup YAML config', default=['dipdup.yml'])
@click.option('--env-file', '-e', type=str, multiple=True, help='Path to .env file', default=[])
@click.option('--logging-config', '-l', type=str, help='Path to logging YAML config', default='logging.yml')
@click.pass_context
@cli_wrapper
async def cli(ctx, config: List[str], env_file: List[str], logging_config: str):
    # NOTE: Search in current workdir, fallback to builtin configs
    try:
        path = join(os.getcwd(), logging_config)
        _logging_config = LoggingConfig.load(path)
    except FileNotFoundError:
        path = join(dirname(__file__), 'configs', logging_config)
        _logging_config = LoggingConfig.load(path)
    _logging_config.apply()

    # NOTE: Nothing useful there
    if 'tortoise' not in _logging_config.config['loggers']:
        logging.getLogger('tortoise').setLevel(logging.WARNING)

    # NOTE: Apply env files before loading config
    for env_path in env_file:
        env_path = join(os.getcwd(), env_path)
        if not exists(env_path):
            raise ConfigurationError(f'env file `{env_path}` does not exist')
        _logger.info('Applying env_file `%s`', env_path)
        load_dotenv(env_path, override=True)

    _config = DipDupConfig.load(config)
    # NOTE: Imports will be loaded later if needed
    _config.initialize(skip_imports=True)
    init_sentry(_config)

    try:
        await DipDupCodeGenerator(_config, {}).create_package()
    except Exception as e:
        raise InitializationRequiredError from e

    if _config.spec_version not in spec_version_mapping:
        raise ConfigurationError(f'Unknown `spec_version`, correct ones: {", ".join(spec_version_mapping)}')
    if _config.spec_version != __spec_version__ and ctx.invoked_subcommand != 'migrate':
        reindex = spec_reindex_mapping[__spec_version__]
        raise MigrationRequiredError(_config.spec_version, __spec_version__, reindex)

    ctx.obj = CLIContext(
        config_paths=config,
        config=_config,
        logging_config=_logging_config,
    )


@cli.command(help='Run indexing')
@click.option('--postpone-jobs', is_flag=True, help='Do not start job scheduler until all indexes are synchronized')
@click.option('--early-realtime', is_flag=True, help='Establish a realtime connection before all indexes are synchronized')
@click.option('--merge-subscriptions', is_flag=True, help='Subscribe to all operations/big map diffs during realtime indexing')
@click.option('--metadata-interface', is_flag=True, help='Enable metadata interface')
@click.pass_context
@cli_wrapper
async def run(
    ctx,
    postpone_jobs: bool,
    early_realtime: bool,
    merge_subscriptions: bool,
    metadata_interface: bool,
) -> None:
    config: DipDupConfig = ctx.obj.config
    config.initialize()
    config.advanced.postpone_jobs |= postpone_jobs
    config.advanced.early_realtime |= early_realtime
    config.advanced.merge_subscriptions |= merge_subscriptions
    config.advanced.metadata_interface |= metadata_interface

    set_decimal_context(config.package)

    dipdup = DipDup(config)
    await dipdup.run()


@cli.command(help='Generate missing callbacks and types')
@click.option('--overwrite-types', is_flag=True, help='Regenerate existing types')
@click.option('--keep-schemas', is_flag=True, help='Do not remove JSONSchemas after generating types')
@click.pass_context
@cli_wrapper
async def init(ctx, overwrite_types: bool, keep_schemas: bool) -> None:
    config: DipDupConfig = ctx.obj.config
    dipdup = DipDup(config)
    await dipdup.init(overwrite_types, keep_schemas)


@cli.command(help='Migrate project to the new spec version')
@click.pass_context
@cli_wrapper
async def migrate(ctx):
    config: DipDupConfig = ctx.obj.config
    migrations = DipDupMigrationManager(config, ctx.obj.config_paths)
    await migrations.migrate()


@cli.command(help='Show current status of indexes in database')
@click.pass_context
@cli_wrapper
async def status(ctx):
    config: DipDupConfig = ctx.obj.config
    url = config.database.connection_string
    models = f'{config.package}.models'

    table = [('name', 'status', 'level')]
    async with tortoise_wrapper(url, models):
        async for index in Index.filter().order_by('name'):
            table.append((index.name, index.status.value, index.level))

    echo(tabulate(table, tablefmt='plain'))


@cli.group(help='Commands to manage DipDup configuration')
@click.pass_context
@cli_wrapper
async def config(ctx):
    ...


@config.command(name='export', help='Dump DipDup configuration')
@click.option('--unsafe', is_flag=True, help='')
@click.pass_context
@cli_wrapper
async def config_export(ctx, unsafe: bool) -> None:
    config_yaml = DipDupConfig.load(
        paths=ctx.obj.config.paths,
        environment=unsafe,
    ).dump()
    echo(config_yaml)


@cli.group(help='Manage datasource caches')
@click.pass_context
@cli_wrapper
async def cache(ctx):
    ...


@cache.command(name='clear', help='Clear datasource request caches')
@click.pass_context
@cli_wrapper
async def cache_clear(ctx) -> None:
    FileCache('dipdup', flag='cs').clear()


@cache.command(name='show', help='Show datasource request caches size information')
@click.pass_context
@cli_wrapper
async def cache_show(ctx) -> None:
    cache = FileCache('dipdup', flag='cs')
    size = subprocess.check_output(['du', '-sh', cache.cache_dir]).split()[0].decode('utf-8')
    echo(f'{cache.cache_dir}: {len(cache)} items, {size}')


@cli.group(help='Hasura integration related commands')
@click.pass_context
@cli_wrapper
async def hasura(ctx):
    ...


@hasura.command(name='configure', help='Configure Hasura GraphQL Engine')
@click.option('--force', is_flag=True, help='Proceed even if Hasura is already configured')
@click.pass_context
@cli_wrapper
async def hasura_configure(ctx, force: bool):
    config: DipDupConfig = ctx.obj.config
    url = config.database.connection_string
    models = f'{config.package}.models'
    if not config.hasura:
        raise ConfigurationError('`hasura` config section is empty')
    hasura_gateway = HasuraGateway(
        package=config.package,
        hasura_config=config.hasura,
        database_config=cast(PostgresDatabaseConfig, config.database),
    )

    async with tortoise_wrapper(url, models):
        async with hasura_gateway:
            await hasura_gateway.configure(force)


@cli.group(help='Manage database schema')
@click.pass_context
@cli_wrapper
async def schema(ctx):
    ...


@schema.command(name='approve', help='Continue to use existing schema after reindexing was triggered')
@click.pass_context
@cli_wrapper
async def schema_approve(ctx):
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


@schema.command(name='wipe', help='Drop all database tables, functions and views')
@click.option('--immune', is_flag=True, help='Drop immune tables too')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
@cli_wrapper
async def schema_wipe(ctx, immune: bool, force: bool):
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
        conn = get_connection(None)
        if isinstance(config.database, PostgresDatabaseConfig):
            await wipe_schema(
                conn=conn,
                name=config.database.schema_name,
                # NOTE: Don't be confused by the name of `--immune` flag, we want to drop all tables if it's set.
                immune_tables=config.database.immune_tables if not immune else (),
            )
        else:
            await Tortoise._drop_databases()

    _logger.info('Schema wiped')


@schema.command(name='init', help='Initialize database schema')
@click.pass_context
@cli_wrapper
async def schema_init(ctx):
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
        conn = get_connection(None)
        sql_path = join(dirname(__file__), 'sql', 'on_reindex')
        await execute_sql_scripts(conn, sql_path)

    _logger.info('Schema initialized')


@schema.command(name='export', help='Print schema SQL including `on_reindex` hook')
@click.pass_context
@cli_wrapper
async def schema_export(ctx):
    config: DipDupConfig = ctx.obj.config
    url = config.database.connection_string
    models = f'{config.package}.models'

    async with tortoise_wrapper(url, models):
        conn = get_connection(None)
        output = get_schema_sql(conn, False) + '\n'
        dipdup_sql_path = join(dirname(__file__), 'sql', 'on_reindex')
        project_sql_path = join(config.package_path, 'sql', 'on_reindex')

        for sql_path in (dipdup_sql_path, project_sql_path):
            for file in iter_files(sql_path):
                output += file.read() + '\n'

        echo(output)
