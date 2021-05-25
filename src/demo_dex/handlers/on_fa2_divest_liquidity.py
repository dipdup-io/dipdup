from decimal import Decimal

import demo_dex.models as models
from demo_dex.types.quipuswap_fa2.parameter.divest_liquidity import DivestLiquidityParameter
from demo_dex.types.quipuswap_fa2.storage import QuipuswapFa2Storage
from demo_dex.types.token_fa2.parameter.transfer import TransferParameter
from demo_dex.types.token_fa2.storage import TokenFa2Storage
from dipdup.models import OperationHandlerContext, TransactionContext


async def on_fa2_divest_liquidity(
    ctx: OperationHandlerContext,
    divest_liquidity: TransactionContext[DivestLiquidityParameter, QuipuswapFa2Storage],
    transfer: TransactionContext[TransferParameter, TokenFa2Storage],
) -> None:

    if ctx.template_values is None:
        raise Exception('This index must be templated')

    storage = divest_liquidity.storage

    decimals = int(ctx.template_values['decimals'])
    symbol, _ = await models.Symbol.get_or_create(symbol=ctx.template_values['symbol'])
    trader, _ = await models.Trader.get_or_create(address=divest_liquidity.data.sender_address)

    position, _ = await models.Position.get_or_create(trader=trader, symbol=symbol)
    transaction = next(op for op in ctx.operations if op.amount)

    assert transaction.amount is not None
    tez_qty = Decimal(transaction.amount) / (10 ** 6)
    token_qty = sum(Decimal(tx.amount) for tx in transfer.parameter.__root__[0].txs) / (10 ** decimals)
    shares_qty = int(divest_liquidity.parameter.shares)

    tez_pool = Decimal(storage.storage.tez_pool) / (10 ** 6)
    token_pool = Decimal(storage.storage.token_pool) / (10 ** decimals)
    if tez_pool and token_pool:
        price = tez_pool / token_pool
        share_px = (tez_qty + price * token_qty) / shares_qty
    else:
        last_trade = await models.Trade.filter(symbol=symbol).order_by('-id').first()

        if last_trade:
            price = last_trade.price
            share_px = (tez_qty + price * token_qty) / shares_qty

            position.realized_pl += shares_qty * (share_px - position.avg_share_px)
            print(position.shares_qty, shares_qty)
            position.shares_qty -= shares_qty  # type: ignore
            assert position.shares_qty >= 0, divest_liquidity.data.hash
        else:
            # NOTE: MEL token
            position.realized_pl = 0  # type: ignore
            position.shares_qty = 0  # type: ignore

    await position.save()
