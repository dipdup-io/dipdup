from dipdup.context import HandlerContext
from dipdup.models import Transaction

from demo_domains.types.name_registry.parameter.execute import ExecuteParameter
from demo_domains.types.name_registry.storage import NameRegistryStorage


async def on_execute(
    ctx: HandlerContext,
    execute: Transaction[ExecuteParameter, NameRegistryStorage],
) -> None:
    ...
