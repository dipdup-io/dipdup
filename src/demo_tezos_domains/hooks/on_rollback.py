
from dipdup.datasources.datasource import Datasource
from dipdup.context import HookContext

async def on_rollback(
    datasource: Datasource,
    ctx: HookContext,
    to_level: int,
    from_level: int,
) -> None:
    ...