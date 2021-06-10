import demo_registrydao.models as models
from demo_registrydao.types.registry.storage import RegistryStorage
from dipdup.models import Origination, Transaction
from dipdup.index import OperationHandlerContext


async def on_origination(
    ctx: OperationHandlerContext,
    registry_origination: Origination[RegistryStorage],
) -> None:
    await models.DAO(address=registry_origination.data.originated_contract_address).save()
