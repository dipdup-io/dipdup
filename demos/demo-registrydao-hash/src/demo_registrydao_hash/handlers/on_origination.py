import demo_registrydao_hash.models as models
from demo_registrydao_hash.types.registry.storage import RegistryStorage
from dipdup.context import HandlerContext
from dipdup.models import Origination


async def on_origination(
    ctx: HandlerContext,
    registry_origination: Origination[RegistryStorage],
) -> None:
    await models.DAO(address=registry_origination.data.originated_contract_address).save()
