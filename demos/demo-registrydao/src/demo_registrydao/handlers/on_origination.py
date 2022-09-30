from dipdup.context import HandlerContext
from dipdup.models import Origination

import demo_registrydao.models as models
from demo_registrydao.types.registry.storage import RegistryStorage


async def on_origination(
    ctx: HandlerContext,
    registry_origination: Origination[RegistryStorage],
) -> None:
    await models.DAO(address=registry_origination.data.originated_contract_address).save()
