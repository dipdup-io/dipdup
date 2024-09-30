from collections.abc import Iterable
from typing import TYPE_CHECKING

from aerich import Command as AerichCommand
from tortoise.backends.base.config_generator import generate_config

from dipdup.config import DipDupConfig

if TYPE_CHECKING:
    from collections.abc import Iterable
    from types import ModuleType


async def create_aerich_command(config: DipDupConfig) -> AerichCommand:
    """Create an `AerichCommand` instance with the database config in `DipDupConfig`.

    The AerichCommand is the entry point to manage database migrations using aerich.
    """
    db_url = config.database.connection_string
    # TODO: Refactor building the app_modules dict and use here and in the tortoise_wrapper function ?
    # Or maybe add the tortoise_config to config ?
    app_modules: dict[str, Iterable[str | ModuleType]] = {'models': [f'{config.package}.models', 'aerich.models']}
    tortoise_config = generate_config(db_url=db_url, app_modules=app_modules)
    return AerichCommand(tortoise_config=tortoise_config, app='models', location=config.database.migrations_dir)
