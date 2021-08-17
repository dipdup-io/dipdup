
from dipdup.context import HookContext
from dipdup.datasources.datasource import Datasource

async def on_rollback(
    ctx: HookContext,
    to_level: int,
    from_level: int,
    datasource: Datasource,
) -> None:
    ...