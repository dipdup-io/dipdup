from demo_domains.handlers.on_storage_diff import on_storage_diff
from demo_domains.types.name_registry.parameter.admin_update import AdminUpdateParameter
from demo_domains.types.name_registry.storage import NameRegistryStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktTransaction


async def on_admin_update(
    ctx: HandlerContext,
    admin_update: TzktTransaction[AdminUpdateParameter, NameRegistryStorage],
) -> None:
    storage = admin_update.storage
    await on_storage_diff(ctx, storage)
