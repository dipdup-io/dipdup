import demo_dao.models as models
from demo_dao.types.registry.tezos_parameters.propose import ProposeParameter
from demo_dao.types.registry.tezos_storage import RegistryStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktTransaction


async def on_propose(
    ctx: HandlerContext,
    propose: TzktTransaction[ProposeParameter, RegistryStorage],
) -> None:
    dao = await models.DAO.get(address=propose.data.target_address)
    await models.Proposal(dao=dao).save()