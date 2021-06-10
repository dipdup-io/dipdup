from demo_tezos_domains.handlers.on_storage_diff import on_storage_diff
from demo_tezos_domains.types.name_registry.parameter.execute import ExecuteParameter
from demo_tezos_domains.types.name_registry.storage import NameRegistryStorage
from dipdup.index import OperationHandlerContext
from dipdup.models import Transaction


async def on_execute(
    ctx: OperationHandlerContext,
    execute: Transaction[ExecuteParameter, NameRegistryStorage],
) -> None:
    storage = execute.storage
    await on_storage_diff(storage)
