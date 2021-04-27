from decimal import Decimal

import demo_quipuswap.models as models
from demo_quipuswap.types.fa12_token.parameter.transfer import Transfer as TransferParameter
from demo_quipuswap.types.fa12_token.storage import Storage as Fa12TokenStorage
from demo_quipuswap.types.quipu_fa12.parameter.divest_liquidity import DivestLiquidity as DivestLiquidityParameter
from demo_quipuswap.types.quipu_fa12.storage import Storage as QuipuFa12Storage
from dipdup.models import HandlerContext, OperationContext


async def on_fa12_divest_liquidity(
    ctx: HandlerContext,
    divest_liquidity: OperationContext[DivestLiquidityParameter, QuipuFa12Storage],
    transfer: OperationContext[TransferParameter, Fa12TokenStorage],
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
    token_qty = Decimal(transfer.parameter.value) / (10 ** decimals)
    shares_qty = int(divest_liquidity.parameter.shares)

    price = (Decimal(storage.storage.tez_pool) / (10 ** 6)) / (Decimal(storage.storage.token_pool) / (10 ** decimals))
    share_px = (tez_qty + price * token_qty) / shares_qty

    position.realized_pl += shares_qty * (share_px - position.avg_share_px)
    position.shares_qty -= shares_qty  # type: ignore
    assert position.shares_qty >= 0, divest_liquidity.data.hash

    await position.save()
