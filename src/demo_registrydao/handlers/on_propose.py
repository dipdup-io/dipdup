import demo_registrydao.models as models
from demo_registrydao.types.registry.parameter.propose import Propose as ProposeParameter
from demo_registrydao.types.registry.storage import Storage as RegistryStorage
from dipdup.models import OperationContext, OperationHandlerContext


async def on_propose(
    ctx: OperationHandlerContext,
    propose: OperationContext[ProposeParameter, RegistryStorage],
) -> None:
    print(propose.storage)
