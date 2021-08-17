from dipdup.context import HookContext
from dipdup.datasources.datasource import Datasource


async def on_rollback(
    datasource: Datasource,
    ctx: HookContext,
    to_level: int,
    from_level: int,
) -> None:
    ...
