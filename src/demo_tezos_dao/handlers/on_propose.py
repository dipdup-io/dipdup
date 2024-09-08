import demo_tezos_dao.models as models
from demo_tezos_dao.types.registry.tezos_parameters.propose import ProposeParameter
from demo_tezos_dao.types.registry.tezos_storage import RegistryStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosTransaction


async def on_propose(
    ctx: HandlerContext,
    propose: TezosTransaction[ProposeParameter, RegistryStorage],
) -> None:
    dao = await models.DAO.get(address=propose.data.target_address)
    await models.Proposal(dao=dao).save()
