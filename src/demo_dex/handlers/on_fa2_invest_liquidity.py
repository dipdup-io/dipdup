from decimal import Decimal

import demo_dex.models as models
from demo_dex.types.fa2_token.tezos_parameters.transfer import TransferParameter
from demo_dex.types.fa2_token.tezos_storage import Fa2TokenStorage
from demo_dex.types.quipu_fa2.tezos_parameters.invest_liquidity import InvestLiquidityParameter
from demo_dex.types.quipu_fa2.tezos_storage import QuipuFa2Storage
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktTransaction


async def on_fa2_invest_liquidity(
    ctx: HandlerContext,
    invest_liquidity: TzktTransaction[InvestLiquidityParameter, QuipuFa2Storage],
    transfer: TzktTransaction[TransferParameter, Fa2TokenStorage],
) -> None:
    storage = invest_liquidity.storage

    decimals = int(ctx.template_values['decimals'])
    symbol = ctx.template_values['symbol']
    trader = invest_liquidity.data.sender_address

    assert trader is not None

    position, _ = await models.Position.get_or_create(trader=trader, symbol=symbol)

    assert invest_liquidity.data.amount is not None
    tez_qty = Decimal(invest_liquidity.data.amount) / (10**6)
    token_qty = sum(Decimal(tx.amount) for tx in transfer.parameter.__root__[0].txs) / (10**decimals)
    new_shares_qty = int(storage.storage.ledger[trader].balance) + int(storage.storage.ledger[trader].frozen_balance)

    price = (Decimal(storage.storage.tez_pool) / (10**6)) / (Decimal(storage.storage.token_pool) / (10**decimals))
    value = tez_qty + price * token_qty
    share_px = value / (new_shares_qty - position.shares_qty)
    assert share_px > 0, invest_liquidity.data.hash

    position.avg_share_px = (position.shares_qty * position.avg_share_px + value) / new_shares_qty
    position.shares_qty = new_shares_qty

    await position.save()