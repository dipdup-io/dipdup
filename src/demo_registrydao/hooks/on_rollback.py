
from dipdup.datasources.datasource import Datasource
from dipdup.context import HookContext

async def on_rollback(
    ctx: HookContext,
    from_level: int,
    datasource: Datasource,
    to_level: int,
) -> None:
    ...