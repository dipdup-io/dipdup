from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.models import *
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.drop_proposal import DropProposal


async def on_drop_proposal(
    ctx: HandlerContext,
    drop_proposal: OperationContext[DropProposal],
) -> None:
    ...
