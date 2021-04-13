import demo_quipuswap.models as models
from demo_quipuswap.types.quipu_fa2.parameter.invest_liquidity import InvestLiquidity
from dipdup.models import HandlerContext, OperationContext


async def on_fa20_invest_liquidity(
    ctx: HandlerContext,
    invest_liquidity: OperationContext[InvestLiquidity],
) -> None:
    ...
