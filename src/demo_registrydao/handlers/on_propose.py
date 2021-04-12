from dipdup.models import HandlerContext, OperationContext

from demo_registrydao.models import *

from demo_registrydao.types.registry.parameter.propose import Propose


async def on_propose(
    ctx: HandlerContext,
    propose: OperationContext[Propose],
) -> None:
    print(ctx)
    print(propose)