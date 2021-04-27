from decimal import Decimal

import demo_quipuswap.models as models
from demo_quipuswap.types.fa2_token.parameter.transfer import Transfer as TransferParameter
from demo_quipuswap.types.fa2_token.storage import Storage as Fa2TokenStorage
from demo_quipuswap.types.quipu_fa2.parameter.divest_liquidity import DivestLiquidity as DivestLiquidityParameter
from demo_quipuswap.types.quipu_fa2.storage import Storage as QuipuFa2Storage
from dipdup.models import OperationContext, OperationHandlerContext


async def on_fa20_divest_liquidity(
    ctx: OperationHandlerContext,
    divest_liquidity: OperationContext[DivestLiquidityParameter, QuipuFa2Storage],
    transfer: OperationContext[TransferParameter, Fa2TokenStorage],
) -> None:

    if ctx.template_values is None:
        raise Exception('This index must be templated')

    storage = divest_liquidity.storage

    decimals = int(ctx.template_values['decimals'])
    symbol = ctx.template_values['symbol']
    trader = divest_liquidity.data.sender_address

    position, _ = await models.Position.get_or_create(trader=trader, symbol=symbol)
    transaction = next(op for op in ctx.operations if op.amount)

    tez_qty = Decimal(transaction.amount) / (10 ** 6)
    token_qty = Decimal(transfer.parameter.__root__[0].txs[0].amount) / (10 ** decimals)
    shares_qty = int(divest_liquidity.parameter.shares)

    price = (Decimal(storage.storage.tez_pool) / (10 ** 6)) / (Decimal(storage.storage.token_pool) / (10 ** decimals))
    share_px = (tez_qty + price * token_qty) / shares_qty

    position.realized_pl += shares_qty * (share_px - position.avg_share_px)
    position.shares_qty -= shares_qty  # type: ignore
    assert position.shares_qty >= 0, divest_liquidity.data.hash

    await position.save()
