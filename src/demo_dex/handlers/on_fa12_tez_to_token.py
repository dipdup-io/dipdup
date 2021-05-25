from decimal import Decimal

import demo_dex.models as models
from demo_dex.types.quipuswap_fa12.parameter.tez_to_token_payment import TezToTokenPaymentParameter
from demo_dex.types.quipuswap_fa12.storage import QuipuswapFa12Storage
from demo_dex.types.token_fa12.parameter.transfer import TransferParameter
from demo_dex.types.token_fa12.storage import TokenFa12Storage
from dipdup.models import OperationHandlerContext, TransactionContext


async def on_fa12_tez_to_token(
    ctx: OperationHandlerContext,
    tez_to_token_payment: TransactionContext[TezToTokenPaymentParameter, QuipuswapFa12Storage],
    transfer: TransactionContext[TransferParameter, TokenFa12Storage],
) -> None:
    if ctx.template_values is None:
        raise Exception('This index must be templated')

    decimals = int(ctx.template_values['decimals'])
    symbol, _ = await models.Symbol.get_or_create(symbol=ctx.template_values['symbol'])
    trader, _ = await models.Trader.get_or_create(address=tez_to_token_payment.data.sender_address)

    min_token_quantity = Decimal(tez_to_token_payment.parameter.min_out) / (10 ** decimals)
    token_quantity = Decimal(transfer.parameter.value) / (10 ** decimals)
    assert tez_to_token_payment.data.amount is not None
    tez_quantity = Decimal(tez_to_token_payment.data.amount) / (10 ** 6)
    assert min_token_quantity <= token_quantity, tez_to_token_payment.data.hash

    trade = models.Trade(
        symbol=symbol,
        trader=trader,
        side=models.TradeSide.BUY,
        quantity=token_quantity,
        price=token_quantity / tez_quantity,
        slippage=(1 - (min_token_quantity / token_quantity)).quantize(Decimal('0.000001')),
        level=transfer.data.level,
        timestamp=transfer.data.timestamp,
    )
    await trade.save()

    trader.trades_qty += 1  # type: ignore
    trader.trades_amount += tez_quantity  # type: ignore
    await trader.save()
