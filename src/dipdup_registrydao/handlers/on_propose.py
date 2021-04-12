from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.models import *
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.propose import Propose


async def on_propose(
    ctx: HandlerContext,
    propose: OperationContext[Propose],
) -> None:
    ...
