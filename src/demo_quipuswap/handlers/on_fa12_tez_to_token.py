import demo_quipuswap.models as models
from demo_quipuswap.types.fa12_token.parameter.transfer import Transfer
from demo_quipuswap.types.quipu_fa12.parameter.tez_to_token_payment import TezToTokenPayment
from dipdup.models import HandlerContext, OperationContext


async def on_fa12_tez_to_token(
    ctx: HandlerContext,
    tez_to_token_payment: OperationContext[TezToTokenPayment],
    transfer: OperationContext[Transfer],
) -> None:
    trader, _ = await models.Trader.get_or_create(address=transfer.parameter.to)
    instrument, _ = await models.Instrument.get_or_create(symbol=ctx.template_values['symbol'])

    min_token_quantity = int(tez_to_token_payment.parameter.min_out)
    token_quantity = int(transfer.parameter.value)
    tez_quantity = int(tez_to_token_payment.data.amount)
    trade = models.Trade(
        instrument=instrument,
        trader=trader,
        side=models.TradeSide.BUY,
        quantity=token_quantity,
        price=token_quantity / tez_quantity,
        slippage=((min_token_quantity / token_quantity) - 1) * 100,
        level=transfer.data.level,
        timestamp=transfer.data.timestamp,
    )
    await trade.save()
