
from dipdup.datasources.datasource import Datasource
from dipdup.context import HookContext

async def on_rollback(
    ctx: HookContext,
    datasource: Datasource,
    from_level: int,
    to_level: int,
) -> None:
    ...