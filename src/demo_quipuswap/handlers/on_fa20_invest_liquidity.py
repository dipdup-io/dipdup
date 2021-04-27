from decimal import Decimal

import demo_quipuswap.models as models
from demo_quipuswap.types.fa2_token.parameter.transfer import Transfer as TransferParameter
from demo_quipuswap.types.fa2_token.storage import Storage as Fa2TokenStorage
from demo_quipuswap.types.quipu_fa2.parameter.invest_liquidity import InvestLiquidity as InvestLiquidityParameter
from demo_quipuswap.types.quipu_fa2.storage import Storage as QuipuFa2Storage
from dipdup.models import HandlerContext, OperationContext


async def on_fa20_invest_liquidity(
    ctx: HandlerContext,
    invest_liquidity: OperationContext[InvestLiquidityParameter, QuipuFa2Storage],
    transfer: OperationContext[TransferParameter, Fa2TokenStorage],
) -> None:

    if ctx.template_values is None:
        raise Exception('This index must be templated')

    storage = invest_liquidity.storage

    decimals = int(ctx.template_values['decimals'])
    symbol = ctx.template_values['symbol']
    trader = invest_liquidity.data.sender_address

    position, _ = await models.Position.get_or_create(trader=trader, symbol=symbol)

    tez_qty = Decimal(invest_liquidity.data.amount) / (10 ** 6)
    token_qty = Decimal(transfer.parameter.__root__[0].txs[0].amount) / (10 ** decimals)
    new_shares_qty = int(storage.storage.ledger[trader].balance) + int(storage.storage.ledger[trader].frozen_balance)

    price = (Decimal(storage.storage.tez_pool) / (10 ** 6)) / (Decimal(storage.storage.token_pool) / (10 ** decimals))
    value = tez_qty + price * token_qty
    share_px = value / (new_shares_qty - position.shares_qty)
    assert share_px > 0, invest_liquidity.data.hash

    position.avg_share_px = (position.shares_qty * position.avg_share_px + value) / new_shares_qty
    position.shares_qty = new_shares_qty  # type: ignore

    await position.save()
