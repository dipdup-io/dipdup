from demo_registrydao.models import *
from demo_registrydao.types.registry.parameter.propose import Propose
from dipdup.models import HandlerContext, OperationContext


async def on_propose(
    ctx: HandlerContext,
    propose: OperationContext[Propose],
) -> None:
    print(propose.storage)
