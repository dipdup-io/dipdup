import demo_quipuswap.models as models
from demo_quipuswap.types.quipu_fa2.parameter.divest_liquidity import DivestLiquidity
from dipdup.models import HandlerContext, OperationContext


async def on_fa20_divest_liquidity(
    ctx: HandlerContext,
    divest_liquidity: OperationContext[DivestLiquidity],
) -> None:
    ...
