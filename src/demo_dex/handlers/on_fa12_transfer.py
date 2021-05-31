from typing import Optional

import demo_dex.models as models
from demo_dex.types.quipuswap_fa12.parameter.transfer import TransferParameter
from demo_dex.types.quipuswap_fa12.storage import QuipuswapFa12Storage
from dipdup.models import OperationData, OperationHandlerContext, OriginationContext, TransactionContext


async def on_fa12_transfer(
    ctx: OperationHandlerContext,
    transfer: TransactionContext[TransferParameter, QuipuswapFa12Storage],
) -> None:
    if ctx.template_values is None:
        raise Exception('This index must be templated')

    symbol, _ = await models.Symbol.get_or_create(symbol=ctx.template_values['symbol'])
    from_trader, _ = await models.Trader.get_or_create(address=transfer.parameter.from_)
    to_trader, _ = await models.Trader.get_or_create(address=transfer.parameter.to)
    value = int(transfer.parameter.value)

    from_position, _ = await models.Position.get_or_create(trader=from_trader, symbol=symbol)
    from_position.shares_qty -= value  # type: ignore
    assert from_position.shares_qty >= 0, transfer.data.hash
    await from_position.save()

    to_position, _ = await models.Position.get_or_create(trader=to_trader, symbol=symbol)
    to_position.shares_qty += value  # type: ignore
    assert to_position.shares_qty >= 0, transfer.data.hash
    await to_position.save()
