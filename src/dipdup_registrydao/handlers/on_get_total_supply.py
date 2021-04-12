from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.models import *
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.get_total_supply import GetTotalSupply


async def on_get_total_supply(
    ctx: HandlerContext,
    get_total_supply: OperationContext[GetTotalSupply],
) -> None:
    ...
