import fileinput
import logging
import os
from dataclasses import dataclass
from functools import wraps
from os.path import dirname, exists, join
from typing import List, cast

import asyncclick as click
import sentry_sdk
from dotenv import load_dotenv
from fcache.cache import FileCache  # type: ignore
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from dipdup import __spec_version__, __version__, spec_reindex_mapping, spec_version_mapping
from dipdup.codegen import DEFAULT_DOCKER_ENV_FILE, DEFAULT_DOCKER_IMAGE, DEFAULT_DOCKER_TAG, DipDupCodeGenerator
from dipdup.config import DipDupConfig, LoggingConfig, PostgresDatabaseConfig
from dipdup.dipdup import DipDup
from dipdup.exceptions import ConfigurationError, DipDupError, MigrationRequiredError
from dipdup.hasura import HasuraGateway
from dipdup.utils import set_decimal_context, tortoise_wrapper

_logger = logging.getLogger('dipdup.cli')


@dataclass
class CLIContext:
    config_paths: List[str]
    config: DipDupConfig
    logging_config: LoggingConfig


def cli_wrapper(fn):
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except KeyboardInterrupt:
            pass
        except DipDupError as e:
            _logger.critical(e.__repr__())
            _logger.info(e.format())
            quit(e.exit_code)

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


@click.group()
@click.version_option(__version__)
@click.option('--config', '-c', type=str, multiple=True, help='Path to dipdup YAML config', default=['dipdup.yml'])
@click.option('--env-file', '-e', type=str, multiple=True, help='Path to .env file', default=[])
@click.option('--logging-config', '-l', type=str, help='Path to logging YAML config', default='logging.yml')
@click.pass_context
@cli_wrapper
async def cli(ctx, config: List[str], env_file: List[str], logging_config: str):
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

    if _config.spec_version not in spec_version_mapping:
        raise ConfigurationError('Unknown `spec_version`, correct ones: {}')
    if _config.spec_version != __spec_version__ and ctx.invoked_subcommand != 'migrate':
        reindex = spec_reindex_mapping[__spec_version__]
        raise MigrationRequiredError(None, _config.spec_version, __spec_version__, reindex)

    ctx.obj = CLIContext(
        config_paths=config,
        config=_config,
        logging_config=_logging_config,
    )


@cli.command(help='Run existing dipdup project')
@click.option('--reindex', is_flag=True, help='Drop database and start indexing from scratch')
@click.option('--oneshot', is_flag=True, help='Synchronize indexes wia REST and exit without starting WS connection')
@click.pass_context
@cli_wrapper
async def run(ctx, reindex: bool, oneshot: bool) -> None:
    config: DipDupConfig = ctx.obj.config
    config.initialize()
    set_decimal_context(config.package)
    dipdup = DipDup(config)
    await dipdup.run(reindex, oneshot)


@cli.command(help='Initialize new dipdup project')
@click.pass_context
@cli_wrapper
async def init(ctx):
    config: DipDupConfig = ctx.obj.config
    config.pre_initialize()
    dipdup = DipDup(config)
    await dipdup.init()


@cli.command(help='Migrate project to the new spec version')
@click.pass_context
@cli_wrapper
async def migrate(ctx):
    def _bump_spec_version(spec_version: str):
        for config_path in ctx.obj.config_paths:
            for line in fileinput.input(config_path, inplace=True):
                if 'spec_version' in line:
                    print(f'spec_version: {spec_version}')
                else:
                    print(line.rstrip())

    config: DipDupConfig = ctx.obj.config
    config.pre_initialize()

    if config.spec_version == __spec_version__:
        _logger.error('Project is already at latest version')
    elif config.spec_version == '0.1':
        await DipDup(config).migrate_to_v10()
        _bump_spec_version('1.0')
    elif config.spec_version == '1.0':
        await DipDup(config).migrate_to_v11()
        _bump_spec_version('1.1')
    else:
        raise ConfigurationError('Unknown `spec_version`')


@cli.command(help='Clear development request cache')
@click.pass_context
@cli_wrapper
async def clear_cache(ctx):
    FileCache('dipdup', flag='cs').clear()


@cli.group()
@click.pass_context
@cli_wrapper
async def docker(ctx):
    ...


@docker.command(name='init')
@click.option('--image', '-i', type=str, help='DipDup Docker image', default=DEFAULT_DOCKER_IMAGE)
@click.option('--tag', '-t', type=str, help='DipDup Docker tag', default=DEFAULT_DOCKER_TAG)
@click.option('--env-file', '-e', type=str, help='Path to env_file', default=DEFAULT_DOCKER_ENV_FILE)
@click.pass_context
@cli_wrapper
async def docker_init(ctx, image: str, tag: str, env_file: str):
    config: DipDupConfig = ctx.obj.config
    await DipDupCodeGenerator(config, {}).generate_docker(image, tag, env_file)


@cli.group()
@click.pass_context
@cli_wrapper
async def hasura(ctx):
    ...


@hasura.command(name='configure', help='Configure Hasura GraphQL Engine')
@click.option('--reset', is_flag=True, help='Reset metadata before configuring')
@click.pass_context
@cli_wrapper
async def hasura_configure(ctx, reset: bool):
    config: DipDupConfig = ctx.obj.config
    url = config.database.connection_string
    models = f'{config.package}.models'
    if not config.hasura:
        _logger.error('`hasura` config section is empty')
        return
    hasura_gateway = HasuraGateway(config.package, config.hasura, cast(PostgresDatabaseConfig, config.database))

    async with tortoise_wrapper(url, models):
        async with hasura_gateway:
            await hasura_gateway.configure(reset)
