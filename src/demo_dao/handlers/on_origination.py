import demo_dao.models as models
from demo_dao.types.registry.tezos_storage import RegistryStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TezosTzktOrigination


async def on_origination(
    ctx: HandlerContext,
    registry_origination: TezosTzktOrigination[RegistryStorage],
) -> None:
    await models.DAO(address=registry_origination.data.originated_contract_address).save()