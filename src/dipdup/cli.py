import asyncio
import fileinput
import logging
import os
from dataclasses import dataclass
from functools import wraps
from os.path import dirname, join
from typing import List, NoReturn

import click
from fcache.cache import FileCache  # type: ignore

from dipdup import __spec_version__, __version__
from dipdup.config import DipDupConfig, LoggingConfig
from dipdup.dipdup import DipDup

_logger = logging.getLogger(__name__)

spec_version_to_version = {
    '0.1': 'dipdup <0.4.3',
    '1.0': 'dipdup ^1.0.0',
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
    if _config.spec_version != __spec_version__ and ctx.invoked_subcommand != 'migrate':
        migration_required(_config.spec_version, __spec_version__)

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
    config: DipDupConfig = ctx.obj.config
    config.pre_initialize()
    await DipDup(config).migrate()

    for config_path in ctx.obj.config_paths:
        for line in fileinput.input(config_path, inplace=True):
            if 'spec_version' in line:
                print(f'spec_version: {__spec_version__}')
            else:
                print(line.rstrip())


@cli.command(help='Clear development request cache')
@click.pass_context
@click_async
async def clear_cache(ctx):
    FileCache('dipdup', flag='cs').clear()
