from demo_quipuswap.models import *
from demo_quipuswap.types.quipu_fa12.parameter.divest_liquidity import DivestLiquidity
from dipdup.models import HandlerContext, OperationContext


async def on_fa12_divest_liquidity(
    ctx: HandlerContext,
    divest_liquidity: OperationContext[DivestLiquidity],
) -> None:
    ...
