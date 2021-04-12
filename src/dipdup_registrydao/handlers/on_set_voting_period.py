from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.models import *
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.set_voting_period import SetVotingPeriod


async def on_set_voting_period(
    ctx: HandlerContext,
    set_voting_period: OperationContext[SetVotingPeriod],
) -> None:
    ...
