import demo_registrydao.models as models
from demo_registrydao.types.registry.storage import RegistryStorage
from dipdup.context import BigMapHandlerContext, HandlerContext, OperationHandlerContext
from dipdup.models import BigMapData, BigMapDiff, OperationData, Origination, Transaction


async def on_origination(
    ctx: OperationHandlerContext,
    registry_origination: Origination[RegistryStorage],
) -> None:
    await models.DAO(address=registry_origination.data.originated_contract_address).save()
