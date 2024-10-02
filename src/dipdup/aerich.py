from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path
    from types import ModuleType

    from aerich import Command as AerichCommand  # type: ignore[import-untyped]


async def create_aerich_command(db_url: str, package: str, migrations_dir: 'Path') -> 'AerichCommand':
    """Create and return an `AerichCommand` instance

    The AerichCommand is the entry point to manage database migrations using aerich.
    """
    from aerich import Command as AerichCommand
    from tortoise.backends.base.config_generator import generate_config

    # TODO: Refactor building the app_modules dict and use here and in the tortoise_wrapper function ?
    # Or maybe add the tortoise_config to database config ?
    app_modules: dict[str, Iterable[str | ModuleType]] = {'models': [f'{package}.models', 'aerich.models']}
    tortoise_config = generate_config(db_url=db_url, app_modules=app_modules)
    return AerichCommand(tortoise_config=tortoise_config, app='models', location=migrations_dir.as_posix())
