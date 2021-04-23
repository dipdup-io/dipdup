from typing import cast

from demo_tezos_domains.handlers.on_storage_diff import on_storage_diff
from demo_tezos_domains.types.name_registry.parameter.execute import Execute
from demo_tezos_domains.types.name_registry.storage import Storage as NameRegistryStorage
from dipdup.models import HandlerContext, OperationContext


async def on_execute(
    ctx: HandlerContext,
    execute: OperationContext[Execute],
) -> None:
    storage = cast(NameRegistryStorage, execute.storage)  # FIXME: remove
    await on_storage_diff(storage)
