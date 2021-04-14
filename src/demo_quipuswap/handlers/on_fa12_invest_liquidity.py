from decimal import Decimal
import demo_quipuswap.models as models
from demo_quipuswap.types.fa12_token.parameter.transfer import Transfer
from demo_quipuswap.types.quipu_fa12.parameter.invest_liquidity import InvestLiquidity
from dipdup.models import HandlerContext, OperationContext


async def on_fa12_invest_liquidity(
    ctx: HandlerContext,
    invest_liquidity: OperationContext[InvestLiquidity],
    transfer: OperationContext[Transfer],
) -> None:

    if ctx.template_values is None:
        raise Exception('This index must be templated')

    decimals = int(ctx.template_values['decimals'])
    trader, _ = await models.Trader.get_or_create(address=invest_liquidity.data.sender_address)
    instrument, _ = await models.Instrument.get_or_create(symbol=ctx.template_values['symbol'])
    position, _ = await models.Position.get_or_create(trader=trader, instrument=instrument)

    position.tez_qty += Decimal(invest_liquidity.data.amount) / (10 ** 6)  # type: ignore
    position.token_qty += Decimal(transfer.parameter.value) / (10 ** decimals)
    await position.save()