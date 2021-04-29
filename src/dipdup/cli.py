import asyncio
import logging
import os
from dataclasses import dataclass
from functools import wraps
from os.path import dirname, join
from typing import List

import click
from fcache.cache import FileCache  # type: ignore

from dipdup import __version__
from dipdup.config import DipDupConfig, LoggingConfig
from dipdup.dipdup import DipDup

_logger = logging.getLogger(__name__)


def click_async(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))

    return wrapper


@dataclass
class CLIContext:
    config: DipDupConfig
    logging_config: LoggingConfig


@click.group()
@click.version_option(__version__)
@click.option('--config', '-c', type=str, multiple=True, help='Path to dipdup YAML config', default='dipdup.yml')
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

    _logger.info('Loading config')
    _config = DipDupConfig.load(config)

    ctx.obj = CLIContext(
        config=_config,
        logging_config=_logging_config,
    )


@cli.command(help='Run existing dipdup project')
@click.pass_context
@click_async
async def run(ctx) -> None:
    config: DipDupConfig = ctx.obj.config
    dipdup = DipDup(config)
    await dipdup.run()


@cli.command(help='Initialize new dipdup project')
@click.pass_context
@click_async
async def init(ctx):
    config: DipDupConfig = ctx.obj.config
    dipdup = DipDup(config)
    await dipdup.init()


@cli.command(help='Clear development request cache')
@click.pass_context
@click_async
async def clear_cache(ctx):
    FileCache('dipdup', flag='cs').clear()
