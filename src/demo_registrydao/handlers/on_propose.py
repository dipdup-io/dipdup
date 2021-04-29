import demo_registrydao.models as models
from demo_registrydao.types.registry.parameter.propose import ProposeParameter
from demo_registrydao.types.registry.storage import RegistryStorage
from dipdup.models import OperationContext, OperationHandlerContext


async def on_propose(
    ctx: OperationHandlerContext,
    propose: OperationContext[ProposeParameter, RegistryStorage],
) -> None:
    print(propose.storage)
