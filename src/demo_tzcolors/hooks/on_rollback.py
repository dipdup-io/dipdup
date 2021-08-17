from dipdup.context import HookContext
from dipdup.datasources.datasource import Datasource


async def on_rollback(
    ctx: HookContext,
    datasource: Datasource,
    from_level: int,
    to_level: int,
) -> None:
    ...
