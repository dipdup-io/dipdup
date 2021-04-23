from typing import cast

from demo_tezos_domains.handlers.on_storage_diff import on_storage_diff
from demo_tezos_domains.types.name_registry.parameter.admin_update import AdminUpdate
from demo_tezos_domains.types.name_registry.storage import Storage as NameRegistryStorage
from dipdup.models import HandlerContext, OperationContext


async def on_admin_update(
    ctx: HandlerContext,
    admin_update: OperationContext[AdminUpdate],
) -> None:
    storage = cast(NameRegistryStorage, admin_update.storage)  # FIXME: remove
    await on_storage_diff(storage)
