import demo_tezos_domains.models as models
from demo_tezos_domains.handlers.on_storage_diff import on_storage_diff
from demo_tezos_domains.types.name_registry.parameter.admin_update import AdminUpdateParameter
from demo_tezos_domains.types.name_registry.storage import NameRegistryStorage
from dipdup.models import TransactionContext
from dipdup.index import OperationHandlerContext


async def on_admin_update(
    ctx: OperationHandlerContext,
    admin_update: TransactionContext[AdminUpdateParameter, NameRegistryStorage],
) -> None:
    storage = admin_update.storage
    await on_storage_diff(storage)
