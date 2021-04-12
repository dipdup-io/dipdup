from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.models import *
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.accept_ownership import AcceptOwnership


async def on_accept_ownership(
    ctx: HandlerContext,
    accept_ownership: OperationContext[AcceptOwnership],
) -> None:
    ...
