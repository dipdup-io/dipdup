from decimal import Decimal

from dipdup.context import HandlerContext
from dipdup.models import OperationData
from dipdup.models import Transaction

import demo_quipuswap.models as models
from demo_quipuswap.types.fa12_token.parameter.transfer import TransferParameter
from demo_quipuswap.types.fa12_token.storage import Fa12TokenStorage
from demo_quipuswap.types.quipu_fa12.parameter.token_to_tez_payment import TokenToTezPaymentParameter
from demo_quipuswap.types.quipu_fa12.storage import QuipuFa12Storage


async def on_fa12_token_to_tez(
    ctx: HandlerContext,
    token_to_tez_payment: Transaction[TokenToTezPaymentParameter, QuipuFa12Storage],
    transfer: Transaction[TransferParameter, Fa12TokenStorage],
    transaction_0: OperationData,
) -> None:
    decimals = int(ctx.template_values['decimals'])
    symbol = ctx.template_values['symbol']
    trader = token_to_tez_payment.data.sender_address

    min_tez_quantity = Decimal(token_to_tez_payment.parameter.min_out) / (10**6)
    token_quantity = Decimal(token_to_tez_payment.parameter.amount) / (10**decimals)
    assert transaction_0.amount is not None
    tez_quantity = Decimal(transaction_0.amount) / (10**6)
    assert min_tez_quantity <= tez_quantity, token_to_tez_payment.data.hash

    trade = models.Trade(
        symbol=symbol,
        trader=trader,
        side=models.TradeSide.SELL,
        quantity=token_quantity,
        price=token_quantity / tez_quantity,
        slippage=(1 - (min_tez_quantity / tez_quantity)).quantize(Decimal('0.000001')),
        level=transfer.data.level,
        timestamp=transfer.data.timestamp,
    )
    await trade.save()
