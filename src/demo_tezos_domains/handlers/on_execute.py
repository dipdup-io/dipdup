import demo_tezos_domains.models as models
from demo_tezos_domains.handlers.on_storage_diff import on_storage_diff
from demo_tezos_domains.types.name_registry.parameter.execute import ExecuteParameter
from demo_tezos_domains.types.name_registry.storage import NameRegistryStorage
from dipdup.models import Transaction
from dipdup.index import OperationHandlerContext


async def on_execute(
    ctx: OperationHandlerContext,
    execute: Transaction[ExecuteParameter, NameRegistryStorage],
) -> None:
    storage = execute.storage
    await on_storage_diff(storage)
