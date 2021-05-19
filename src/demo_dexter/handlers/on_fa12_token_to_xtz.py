from decimal import Decimal
from typing import Optional

import demo_dexter.models as models
from demo_dexter.types.dexter_fa12.parameter.token_to_xtz import TokenToXtzParameter
from demo_dexter.types.dexter_fa12.storage import DexterFa12Storage
from demo_dexter.types.fa12_token.parameter.transfer import TransferParameter
from demo_dexter.types.fa12_token.storage import Fa12TokenStorage
from dipdup.models import OperationData, OperationHandlerContext, OriginationContext, TransactionContext


async def on_fa12_token_to_xtz(
    ctx: OperationHandlerContext,
    token_to_xtz: TransactionContext[TokenToXtzParameter, DexterFa12Storage],
    transfer: TransactionContext[TransferParameter, Fa12TokenStorage],
) -> None:
    if ctx.template_values is None:
        raise Exception('This index must be templated')

    decimals = int(ctx.template_values['decimals'])
    symbol = ctx.template_values['symbol']
    trader, _ = await models.Trader.get_or_create(address=token_to_xtz.data.sender_address)

    min_tez_quantity = Decimal(token_to_xtz.parameter.minXtzBought) / (10 ** 6)
    token_quantity = Decimal(token_to_xtz.parameter.tokensSold) / (10 ** decimals)
    transaction = next(op for op in ctx.operations if op.amount)
    assert transaction.amount is not None
    tez_quantity = Decimal(transaction.amount) / (10 ** 6)
    assert min_tez_quantity <= tez_quantity, token_to_xtz.data.hash

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

    trader.trades_qty += 1  # type: ignore
    trader.trades_amount += tez_quantity  # type: ignore
    await trader.save()
