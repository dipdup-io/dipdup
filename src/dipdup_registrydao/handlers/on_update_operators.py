from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.models import *
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.update_operators import UpdateOperators


async def on_update_operators(
    ctx: HandlerContext,
    update_operators: OperationContext[UpdateOperators],
) -> None:
    ...
