from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.models import *
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.flush import Flush


async def on_flush(
    ctx: HandlerContext,
    flush: OperationContext[Flush],
) -> None:
    ...
