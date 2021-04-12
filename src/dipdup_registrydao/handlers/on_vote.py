from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.vote import Vote


async def on_vote(
    ctx: HandlerContext,
    vote: OperationContext[Vote],
) -> None:
    ...
