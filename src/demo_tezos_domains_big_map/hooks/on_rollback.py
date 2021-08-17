from dipdup.context import HookContext
from dipdup.datasources.datasource import Datasource


async def on_rollback(
    from_level: int,
    datasource: Datasource,
    to_level: int,
    ctx: HookContext,
) -> None:
    ...
