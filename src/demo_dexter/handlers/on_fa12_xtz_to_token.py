from decimal import Decimal
from typing import Optional

import demo_dexter.models as models
from demo_dexter.types.dexter_fa12.parameter.xtz_to_token import XtzToTokenParameter
from demo_dexter.types.dexter_fa12.storage import DexterFa12Storage
from demo_dexter.types.fa12_token.parameter.transfer import TransferParameter
from demo_dexter.types.fa12_token.storage import Fa12TokenStorage
from dipdup.models import OperationData, OperationHandlerContext, OriginationContext, TransactionContext


async def on_fa12_xtz_to_token(
    ctx: OperationHandlerContext,
    xtz_to_token: TransactionContext[XtzToTokenParameter, DexterFa12Storage],
    transfer: TransactionContext[TransferParameter, Fa12TokenStorage],
) -> None:
    if ctx.template_values is None:
        raise Exception('This index must be templated')

    decimals = int(ctx.template_values['decimals'])
    symbol, _ = await models.Symbol.get_or_create(symbol=ctx.template_values['symbol'])
    trader, _ = await models.Trader.get_or_create(address=xtz_to_token.data.sender_address)

    min_token_quantity = Decimal(xtz_to_token.parameter.minTokensBought) / (10 ** decimals)
    token_quantity = Decimal(transfer.parameter.value) / (10 ** decimals)
    assert xtz_to_token.data.amount is not None
    tez_quantity = Decimal(xtz_to_token.data.amount) / (10 ** 6)
    assert min_token_quantity <= token_quantity, xtz_to_token.data.hash

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
