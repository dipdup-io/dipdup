from dipdup.context import HookContext
from dipdup.datasources.datasource import Datasource
from dipdup.exceptions import CallbackNotImplementedError


async def on_rollback(
    ctx: HookContext,
    datasource: Datasource,
    from_level: int,
    to_level: int,
) -> None:
    await ctx.execute_sql('on_rollback')
    raise CallbackNotImplementedError
