from demo_quipuswap.models import *
from demo_quipuswap.types.quipu_fa12.parameter.invest_liquidity import InvestLiquidity
from dipdup.models import HandlerContext, OperationContext


async def on_fa12_invest_liquidity(
    ctx: HandlerContext,
    invest_liquidity: OperationContext[InvestLiquidity],
) -> None:
    ...
