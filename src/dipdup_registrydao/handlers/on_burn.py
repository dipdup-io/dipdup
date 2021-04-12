from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.models import *
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.burn import Burn


async def on_burn(
    ctx: HandlerContext,
    burn: OperationContext[Burn],
) -> None:
    ...
