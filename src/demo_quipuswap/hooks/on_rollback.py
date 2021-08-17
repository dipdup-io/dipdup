from dipdup.context import HookContext
from dipdup.datasources.datasource import Datasource


async def on_rollback(
    from_level: int,
    ctx: HookContext,
    to_level: int,
    datasource: Datasource,
) -> None:
    ...
