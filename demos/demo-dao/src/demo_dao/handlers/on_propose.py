import demo_dao.models as models
from demo_dao.types.registry.parameter.propose import ProposeParameter
from demo_dao.types.registry.storage import RegistryStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import Transaction


async def on_propose(
    ctx: HandlerContext,
    propose: Transaction[ProposeParameter, RegistryStorage],
) -> None:
    dao = await models.DAO.get(address=propose.data.target_address)
    await models.Proposal(dao=dao).save()
