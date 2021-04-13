from decimal import Decimal
import demo_quipuswap.models as models
from demo_quipuswap.types.fa12_token.parameter.transfer import Transfer
from demo_quipuswap.types.quipu_fa12.parameter.token_to_tez_payment import TokenToTezPayment
from dipdup.models import HandlerContext, OperationContext


async def on_fa12_token_to_tez(
    ctx: HandlerContext,
    token_to_tez_payment: OperationContext[TokenToTezPayment],
    transfer: OperationContext[Transfer],
) -> None:
    decimals = int(ctx.template_values['decimals'])
    trader, _ = await models.Trader.get_or_create(address=transfer.parameter.to)
    instrument, _ = await models.Instrument.get_or_create(symbol=ctx.template_values['symbol'])

    min_tez_quantity = Decimal(token_to_tez_payment.parameter.min_out)
    token_quantity = Decimal(token_to_tez_payment.parameter.amount) / (10 ** decimals)
    transaction = next(op for op in ctx.operations if op.amount)
    tez_quantity = Decimal(transaction.amount) / (10 ** 6)
    trade = models.Trade(
        instrument=instrument,
        trader=trader,
        side=models.TradeSide.SELL,
        quantity=token_quantity,
        price=token_quantity / tez_quantity,
        slippage=((min_tez_quantity / tez_quantity) - 1) * 100,
        level=transfer.data.level,
        timestamp=transfer.data.timestamp,
    )
    await trade.save()
