from decimal import Decimal

import demo_quipuswap.models as models
from demo_quipuswap.types.fa2_token.parameter.transfer import Transfer as TransferParameter
from demo_quipuswap.types.fa2_token.storage import Storage as Fa2TokenStorage
from demo_quipuswap.types.quipu_fa2.parameter.token_to_tez_payment import TokenToTezPayment as TokenToTezPaymentParameter
from demo_quipuswap.types.quipu_fa2.storage import Storage as QuipuFa2Storage
from dipdup.models import OperationHandlerContext, OperationContext


async def on_fa2_token_to_tez(
    ctx: OperationHandlerContext,
    token_to_tez_payment: OperationContext[TokenToTezPaymentParameter, QuipuFa2Storage],
    transfer: OperationContext[TransferParameter, Fa2TokenStorage],
) -> None:
    if ctx.template_values is None:
        raise Exception('This index must be templated')

    decimals = int(ctx.template_values['decimals'])
    symbol = ctx.template_values['symbol']
    trader = token_to_tez_payment.data.sender_address

    min_tez_quantity = Decimal(token_to_tez_payment.parameter.min_out) / (10 ** decimals)
    token_quantity = Decimal(token_to_tez_payment.parameter.amount) / (10 ** decimals)
    transaction = next(op for op in ctx.operations if op.amount)
    tez_quantity = Decimal(transaction.amount) / (10 ** 6)
    assert min_tez_quantity <= tez_quantity, token_to_tez_payment.data.hash

    trade = models.Trade(
        symbol=symbol,
        trader=trader,
        side=models.TradeSide.SELL,
        quantity=token_quantity,
        price=token_quantity / tez_quantity,
        slippage=1 - (min_tez_quantity / tez_quantity),
        level=transfer.data.level,
        timestamp=transfer.data.timestamp,
    )
    await trade.save()
