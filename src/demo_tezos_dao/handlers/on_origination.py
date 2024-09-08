import demo_tezos_dao.models as models
from demo_tezos_dao.types.registry.tezos_storage import RegistryStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosOrigination


async def on_origination(
    ctx: HandlerContext,
    registry_origination: TezosOrigination[RegistryStorage],
) -> None:
    await models.DAO(address=registry_origination.data.originated_contract_address).save()
