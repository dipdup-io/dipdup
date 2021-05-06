import demo_registrydao.models as models
from demo_registrydao.types.registry.storage import RegistryStorage
from dipdup.models import OperationHandlerContext, OriginationContext, TransactionContext


async def on_origination(
    ctx: OperationHandlerContext,
    registry_origination: OriginationContext[RegistryStorage],
) -> None:
    ...
