import demo_registrydao_hash.models as models
from demo_registrydao_hash.types.registry.parameter.propose import ProposeParameter
from demo_registrydao_hash.types.registry.storage import RegistryStorage
from dipdup.context import HandlerContext
from dipdup.models import Transaction


async def on_propose(
    ctx: HandlerContext,
    propose: Transaction[ProposeParameter, RegistryStorage],
) -> None:
    dao = await models.DAO.get(address=propose.data.target_address)
    await models.Proposal(dao=dao).save()
