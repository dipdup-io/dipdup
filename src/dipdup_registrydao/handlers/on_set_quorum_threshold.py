from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.models import *
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.set_quorum_threshold import SetQuorumThreshold


async def on_set_quorum_threshold(
    ctx: HandlerContext,
    set_quorum_threshold: OperationContext[SetQuorumThreshold],
) -> None:
    ...
