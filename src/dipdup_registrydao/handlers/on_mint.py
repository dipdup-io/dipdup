from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.models import *
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.mint import Mint


async def on_mint(
    ctx: HandlerContext,
    mint: OperationContext[Mint],
) -> None:
    ...
