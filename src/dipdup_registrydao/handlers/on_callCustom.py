from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.models import *
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.callCustom import Callcustom


async def on_callCustom(
    ctx: HandlerContext,
    callCustom: OperationContext[Callcustom],
) -> None:
    ...
