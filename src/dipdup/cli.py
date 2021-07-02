import asyncio
import fileinput
import logging
import os
from dataclasses import dataclass
from functools import wraps
from os.path import dirname, join
from typing import List, NoReturn

import click
import sentry_sdk
from fcache.cache import FileCache  # type: ignore
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

from dipdup import __spec_version__, __version__
from dipdup.config import DipDupConfig, LoggingConfig
from dipdup.dipdup import DipDup
from dipdup.exceptions import ConfigurationError

_logger = logging.getLogger(__name__)

spec_version_to_version = {
    '0.1': 'dipdup v0.4.3 and below',
    '1.0': 'dipdup v1.0.0 - v1.1.2',
    '1.1': 'dipdup v1.2.0 and above',
}

migration_required_message = """

Migration required!

project spec version: %s (%s)
current spec version: %s (%s)

  1. Run `dipdup migrate`
  2. Review and commit changes

See https://baking-bad.org/blog/ for additional release information.
"""


def migration_required(from_: str, to: str) -> NoReturn:
    _logger.warning(
        migration_required_message,
        from_,
        spec_version_to_version[from_],
        to,
        spec_version_to_version[to],
    )
    quit()


def click_async(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))

    return wrapper


@dataclass
class CLIContext:
    config_paths: List[str]
    config: DipDupConfig
    logging_config: LoggingConfig


@click.group()
@click.version_option(__version__)
@click.option('--config', '-c', type=str, multiple=True, help='Path to dipdup YAML config', default=['dipdup.yml'])
@click.option('--logging-config', '-l', type=str, help='Path to logging YAML config', default='logging.yml')
@click.pass_context
@click_async
async def cli(ctx, config: List[str], logging_config: str):
    try:
        path = join(os.getcwd(), logging_config)
        _logging_config = LoggingConfig.load(path)
    except FileNotFoundError:
        path = join(dirname(__file__), 'configs', logging_config)
        _logging_config = LoggingConfig.load(path)
    _logging_config.apply()

    _config = DipDupConfig.load(config)
    if _config.spec_version not in spec_version_to_version:
        raise ConfigurationError('Unknown `spec_version`')
    if _config.spec_version != __spec_version__ and ctx.invoked_subcommand != 'migrate':
        migration_required(_config.spec_version, __spec_version__)

    if _config.sentry:
        sentry_sdk.init(
            dsn=_config.sentry.dsn,
            integrations=[AioHttpIntegration()],
        )

    ctx.obj = CLIContext(
        config_paths=config,
        config=_config,
        logging_config=_logging_config,
    )


@cli.command(help='Run existing dipdup project')
@click.option('--reindex', is_flag=True, help='Drop database and start indexing from scratch')
@click.option('--oneshot', is_flag=True, help='Synchronize indexes wia REST and exit without starting WS connection')
@click.pass_context
@click_async
async def run(ctx, reindex: bool, oneshot: bool) -> None:
    config: DipDupConfig = ctx.obj.config
    config.initialize()
    dipdup = DipDup(config)
    await dipdup.run(reindex, oneshot)


@cli.command(help='Initialize new dipdup project')
@click.pass_context
@click_async
async def init(ctx):
    config: DipDupConfig = ctx.obj.config
    config.pre_initialize()
    dipdup = DipDup(config)
    await dipdup.init()


@cli.command(help='Migrate project to the new spec version')
@click.pass_context
@click_async
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
@click_async
async def clear_cache(ctx):
    FileCache('dipdup', flag='cs').clear()
