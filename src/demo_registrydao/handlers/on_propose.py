import demo_registrydao.models as models
from demo_registrydao.types.registry.parameter.propose import ProposeParameter
from demo_registrydao.types.registry.storage import RegistryStorage
from dipdup.models import OriginationContext, TransactionContext
from dipdup.index import OperationHandlerContext

async def on_propose(
    ctx: OperationHandlerContext,
    propose: TransactionContext[ProposeParameter, RegistryStorage],
) -> None:
    dao = await models.DAO.get(address=propose.data.target_address)
    await models.Proposal(dao=dao).save()
