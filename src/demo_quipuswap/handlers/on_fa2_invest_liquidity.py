from decimal import Decimal

import demo_quipuswap.models as models
from demo_quipuswap.types.fa2_token.parameter.transfer import TransferParameter
from demo_quipuswap.types.fa2_token.storage import Fa2TokenStorage
from demo_quipuswap.types.quipu_fa2.parameter.invest_liquidity import InvestLiquidityParameter
from demo_quipuswap.types.quipu_fa2.storage import QuipuFa2Storage
from dipdup.models import OperationHandlerContext, TransactionContext


async def on_fa2_invest_liquidity(
    ctx: OperationHandlerContext,
    invest_liquidity: TransactionContext[InvestLiquidityParameter, QuipuFa2Storage],
    transfer: TransactionContext[TransferParameter, Fa2TokenStorage],
) -> None:

    if ctx.template_values is None:
        raise Exception('This index must be templated')

    storage = invest_liquidity.storage

    decimals = int(ctx.template_values['decimals'])
    symbol = ctx.template_values['symbol']
    trader = invest_liquidity.data.sender_address

    position, _ = await models.Position.get_or_create(trader=trader, symbol=symbol)

    assert invest_liquidity.data.amount is not None
    tez_qty = Decimal(invest_liquidity.data.amount) / (10 ** 6)
    token_qty = sum(Decimal(tx.amount) for tx in transfer.parameter.__root__[0].txs) / (10 ** decimals)
    new_shares_qty = int(storage.storage.ledger[trader].balance) + int(storage.storage.ledger[trader].frozen_balance)  # type: ignore

    price = (Decimal(storage.storage.tez_pool) / (10 ** 6)) / (Decimal(storage.storage.token_pool) / (10 ** decimals))
    value = tez_qty + price * token_qty
    share_px = value / (new_shares_qty - position.shares_qty)
    assert share_px > 0, invest_liquidity.data.hash

    position.avg_share_px = (position.shares_qty * position.avg_share_px + value) / new_shares_qty
    position.shares_qty = new_shares_qty  # type: ignore

    await position.save()
