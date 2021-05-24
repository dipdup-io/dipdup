from decimal import Decimal
from typing import Optional
from demo_quipuswap_dexter.handlers.types import Fa12TokenStorageT, TransferParameterT

import demo_quipuswap_dexter.models as models
from demo_quipuswap_dexter.types.dexter_fa12.parameter.add_liquidity import AddLiquidityParameter
from demo_quipuswap_dexter.types.dexter_fa12.storage import DexterFa12Storage
from demo_quipuswap_dexter.types.fa12_token.parameter.transfer import TransferParameter
from demo_quipuswap_dexter.types.fa12_token.storage import Fa12TokenStorage
from dipdup.models import OperationData, OperationHandlerContext, OriginationContext, TransactionContext


async def on_fa12_add_liquidity(
    ctx: OperationHandlerContext,
    add_liquidity: TransactionContext[AddLiquidityParameter, DexterFa12Storage],
    transfer: TransactionContext[TransferParameterT, Fa12TokenStorageT],
) -> None:
    if ctx.template_values is None:
        raise Exception('This index must be templated')

    storage = add_liquidity.storage

    decimals = int(ctx.template_values['decimals'])
    symbol, _ = await models.Symbol.get_or_create(symbol=ctx.template_values['symbol'])
    trader, _ = await models.Trader.get_or_create(address=add_liquidity.data.sender_address)

    position, _ = await models.Position.get_or_create(trader=trader, symbol=symbol)

    assert add_liquidity.data.amount is not None
    tez_qty = Decimal(add_liquidity.data.amount) / (10 ** 6)
    token_qty = Decimal(transfer.parameter.value) / (10 ** decimals)
    new_shares_qty = int(storage.accounts[trader.address].balance)

    price = (Decimal(storage.xtzPool) / (10 ** 6)) / (Decimal(storage.tokenPool) / (10 ** decimals))
    value = tez_qty + price * token_qty
    share_px = value / (new_shares_qty - position.shares_qty)
    assert share_px > 0, add_liquidity.data.hash

    position.avg_share_px = (position.shares_qty * position.avg_share_px + value) / new_shares_qty
    position.shares_qty = new_shares_qty  # type: ignore

    await position.save()
