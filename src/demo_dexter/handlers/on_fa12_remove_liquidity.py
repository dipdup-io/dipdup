from decimal import Decimal
from typing import Optional

import demo_dexter.models as models
from demo_dexter.types.dexter_fa12.parameter.remove_liquidity import RemoveLiquidityParameter
from demo_dexter.types.dexter_fa12.storage import DexterFa12Storage
from demo_dexter.types.fa12_token.parameter.transfer import TransferParameter
from demo_dexter.types.fa12_token.storage import Fa12TokenStorage
from dipdup.models import OperationData, OperationHandlerContext, OriginationContext, TransactionContext


async def on_fa12_remove_liquidity(
    ctx: OperationHandlerContext,
    remove_liquidity: TransactionContext[RemoveLiquidityParameter, DexterFa12Storage],
    transfer: TransactionContext[TransferParameter, Fa12TokenStorage],
) -> None:
    if ctx.template_values is None:
        raise Exception('This index must be templated')

    storage = remove_liquidity.storage

    decimals = int(ctx.template_values['decimals'])
    symbol, _ = await models.Symbol.get_or_create(symbol=ctx.template_values['symbol'])
    trader, _ = await models.Trader.get_or_create(address=remove_liquidity.data.sender_address)

    position, _ = await models.Position.get_or_create(trader=trader, symbol=symbol)
    transaction = next(op for op in ctx.operations if op.amount)

    assert transaction.amount is not None
    tez_qty = Decimal(transaction.amount) / (10 ** 6)
    token_qty = Decimal(transfer.parameter.value) / (10 ** decimals)
    shares_qty = int(remove_liquidity.parameter.lqtBurned)

    tez_pool = Decimal(storage.xtzPool) / (10 ** 6)
    token_pool = Decimal(storage.tokenPool) / (10 ** decimals)
    if tez_pool and token_pool:
        price = tez_pool / token_pool
    else:
        last_trade = await models.Trade.filter(symbol=symbol).order_by('-id').first()
        assert last_trade
        price = last_trade.price
    share_px = (tez_qty + price * token_qty) / shares_qty

    position.realized_pl += shares_qty * (share_px - position.avg_share_px)
    position.shares_qty -= shares_qty  # type: ignore
    assert position.shares_qty >= 0, remove_liquidity.data.hash

    await position.save()
