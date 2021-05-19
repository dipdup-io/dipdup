from decimal import Decimal

import demo_quipuswap.models as models
from demo_quipuswap.types.fa12_token.parameter.transfer import TransferParameter
from demo_quipuswap.types.fa12_token.storage import Fa12TokenStorage
from demo_quipuswap.types.quipu_fa12.parameter.divest_liquidity import DivestLiquidityParameter
from demo_quipuswap.types.quipu_fa12.storage import QuipuFa12Storage
from dipdup.models import OperationHandlerContext, TransactionContext


async def on_fa12_divest_liquidity(
    ctx: OperationHandlerContext,
    divest_liquidity: TransactionContext[DivestLiquidityParameter, QuipuFa12Storage],
    transfer: TransactionContext[TransferParameter, Fa12TokenStorage],
) -> None:
    if ctx.template_values is None:
        raise Exception('This index must be templated')

    storage = divest_liquidity.storage

    decimals = int(ctx.template_values['decimals'])
    symbol = ctx.template_values['symbol']
    trader, _ = await models.Trader.get_or_create(address=divest_liquidity.data.sender_address)

    position, _ = await models.Position.get_or_create(trader=trader, symbol=symbol)
    transaction = next(op for op in ctx.operations if op.amount)

    assert transaction.amount is not None
    tez_qty = Decimal(transaction.amount) / (10 ** 6)
    token_qty = Decimal(transfer.parameter.value) / (10 ** decimals)
    shares_qty = int(divest_liquidity.parameter.shares)

    tez_pool = Decimal(storage.storage.tez_pool) / (10 ** 6)
    token_pool = Decimal(storage.storage.token_pool) / (10 ** decimals)
    if tez_pool and token_pool:
        price = tez_pool / token_pool
    else:
        last_trade = await models.Trade.filter(symbol=symbol).order_by('-id').first()
        assert last_trade
        price = last_trade.price
    share_px = (tez_qty + price * token_qty) / shares_qty

    position.realized_pl += shares_qty * (share_px - position.avg_share_px)
    position.shares_qty -= shares_qty  # type: ignore
    assert position.shares_qty >= 0, divest_liquidity.data.hash

    await position.save()
