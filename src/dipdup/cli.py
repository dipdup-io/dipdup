import asyncio
import logging
import os
import signal
from dataclasses import dataclass
from functools import wraps
from os import listdir
from os.path import dirname, exists, join
from typing import List, cast

import asyncclick as click
import sentry_sdk
from dotenv import load_dotenv
from fcache.cache import FileCache  # type: ignore
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

import dipdup.context as context
from dipdup import __spec_version__, __version__, spec_reindex_mapping, spec_version_mapping
from dipdup.codegen import DEFAULT_DOCKER_ENV_FILE, DEFAULT_DOCKER_IMAGE, DEFAULT_DOCKER_TAG, DipDupCodeGenerator
from dipdup.config import DipDupConfig, LoggingConfig, PostgresDatabaseConfig
from dipdup.dipdup import DipDup
from dipdup.exceptions import ConfigurationError, DeprecatedHandlerError, DipDupError, MigrationRequiredError
from dipdup.hasura import HasuraGateway
from dipdup.migrations import DipDupMigrationManager, deprecated_handlers
from dipdup.utils.database import set_decimal_context, tortoise_wrapper

_logger = logging.getLogger('dipdup.cli')


@dataclass
class CLIContext:
    config_paths: List[str]
    config: DipDupConfig
    logging_config: LoggingConfig


async def shutdown() -> None:
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
            with DipDupError.wrap():
                await fn(*args, **kwargs)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        except DipDupError as e:
            # FIXME: No traceback in test logs
            _logger.critical(e.__repr__())
            _logger.info(e.format())
            quit(1)

    return wrapper


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
    )


@click.group(help='Docs: https://docs.dipdup.net')
@click.version_option(__version__)
@click.option('--config', '-c', type=str, multiple=True, help='Path to dipdup YAML config', default=['dipdup.yml'])
@click.option('--env-file', '-e', type=str, multiple=True, help='Path to .env file', default=[])
@click.option('--logging-config', '-l', type=str, help='Path to logging YAML config', default='logging.yml')
@click.pass_context
@cli_wrapper
async def cli(ctx, config: List[str], env_file: List[str], logging_config: str):
    # NOTE: Config from cwd, fallback to builtin
    try:
        path = join(os.getcwd(), logging_config)
        _logging_config = LoggingConfig.load(path)
    except FileNotFoundError:
        path = join(dirname(__file__), 'configs', logging_config)
        _logging_config = LoggingConfig.load(path)
    _logging_config.apply()

    # NOTE: Apply env files before loading config
    for env_path in env_file:
        env_path = join(os.getcwd(), env_path)
        if not exists(env_path):
            raise ConfigurationError(f'env file `{env_path}` does not exist')
        _logger.info('Applying env_file `%s`', env_path)
        load_dotenv(env_path, override=True)

    _config = DipDupConfig.load(config)
    init_sentry(_config)

    await DipDupCodeGenerator(_config, {}).create_package()

    if _config.spec_version not in spec_version_mapping:
        raise ConfigurationError(f'Unknown `spec_version`, correct ones: {", ".join(spec_version_mapping)}')
    if _config.spec_version != __spec_version__ and ctx.invoked_subcommand != 'migrate':
        reindex = spec_reindex_mapping[__spec_version__]
        raise MigrationRequiredError(_config.spec_version, __spec_version__, reindex)

    if ctx.invoked_subcommand != 'migrate':
        handlers_path = join(_config.package_path, 'handlers')
        if set(listdir(handlers_path)).intersection(set(deprecated_handlers)):
            raise DeprecatedHandlerError

    ctx.obj = CLIContext(
        config_paths=config,
        config=_config,
        logging_config=_logging_config,
    )


@cli.command(help='Run indexing')
@click.option('--reindex', is_flag=True, help='Drop database and start indexing from scratch')
@click.option('--oneshot', is_flag=True, help='Synchronize indexes wia REST and exit without starting WS connection')
@click.option('--postpone-jobs', is_flag=True, help='Do not start job scheduler until all indexes are synchronized')
@click.option('--forbid-reindexing', is_flag=True, help='Raise exception instead of truncating database when reindexing is triggered')
@click.pass_context
@cli_wrapper
async def run(
    ctx,
    reindex: bool,
    oneshot: bool,
    postpone_jobs: bool,
    forbid_reindexing: bool,
) -> None:
    config: DipDupConfig = ctx.obj.config
    config.initialize()
    set_decimal_context(config.package)
    if forbid_reindexing:
        context.forbid_reindexing = True
    dipdup = DipDup(config)
    await dipdup.run(reindex, oneshot, postpone_jobs)


@cli.command(help='Generate missing callbacks and types')
@click.option('--overwrite-types', is_flag=True, help='Regenerate existing types')
@click.pass_context
@cli_wrapper
async def init(ctx, overwrite_types: bool):
    config: DipDupConfig = ctx.obj.config
    config.initialize(skip_imports=True)
    dipdup = DipDup(config)
    await dipdup.init(overwrite_types)


@cli.command(help='Migrate project to the new spec version')
@click.pass_context
@cli_wrapper
async def migrate(ctx):
    config: DipDupConfig = ctx.obj.config
    config.initialize(skip_imports=True)
    migrations = DipDupMigrationManager(config, ctx.obj.config_paths)
    await migrations.migrate()


# TODO: "cache clear"?
@cli.command(help='Clear development request cache')
@click.pass_context
@cli_wrapper
async def clear_cache(ctx):
    FileCache('dipdup', flag='cs').clear()


@cli.group(help='Docker integration related commands')
@click.pass_context
@cli_wrapper
async def docker(ctx):
    ...


@docker.command(name='init', help='Generate Docker inventory in project directory')
@click.option('--image', '-i', type=str, help='DipDup Docker image', default=DEFAULT_DOCKER_IMAGE)
@click.option('--tag', '-t', type=str, help='DipDup Docker tag', default=DEFAULT_DOCKER_TAG)
@click.option('--env-file', '-e', type=str, help='Path to env_file', default=DEFAULT_DOCKER_ENV_FILE)
@click.pass_context
@cli_wrapper
async def docker_init(ctx, image: str, tag: str, env_file: str):
    config: DipDupConfig = ctx.obj.config
    await DipDupCodeGenerator(config, {}).generate_docker(image, tag, env_file)


@cli.group(help='Hasura integration related commands')
@click.pass_context
@cli_wrapper
async def hasura(ctx):
    ...


@hasura.command(name='configure', help='Configure Hasura GraphQL Engine')
@click.pass_context
@cli_wrapper
async def hasura_configure(ctx):
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
            await hasura_gateway.configure()
