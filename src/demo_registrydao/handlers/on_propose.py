import demo_registrydao.models as models
from demo_registrydao.types.registry.parameter.propose import Propose as ProposeParameter
from demo_registrydao.types.registry.storage import Storage as RegistryStorage
from dipdup.models import HandlerContext, OperationContext


async def on_propose(
    ctx: HandlerContext,
    propose: OperationContext[ProposeParameter, RegistryStorage],
) -> None:
    print(propose.storage)
