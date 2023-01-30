import demo_factories.models as models
from demo_factories.types.registry.storage import RegistryStorage
from dipdup.context import HandlerContext
from dipdup.models.tzkt import Origination


async def on_origination(
    ctx: HandlerContext,
    registry_origination: Origination[RegistryStorage],
) -> None:
    await models.DAO(address=registry_origination.data.originated_contract_address).save()
