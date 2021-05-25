from typing import Optional

from dipdup.models import OperationData, OperationHandlerContext, OriginationContext, TransactionContext

import demo_dex.models as models

from demo_dex.types.quipuswap_fa12.storage import QuipuswapFa12Storage


async def on_fa12_origination(
    ctx: OperationHandlerContext,
    quipuswap_fa12_origination: OriginationContext[QuipuswapFa12Storage],
) -> None:
    if ctx.template_values is None:
        raise Exception('This index must be templated')

    symbol, _ = await models.Symbol.get_or_create(symbol=ctx.template_values['symbol'])

    for address, value in quipuswap_fa12_origination.storage.storage.ledger.items():
        shares_qty = value.balance
        trader, _ = await models.Trader.get_or_create(address=address)
        await models.Position(trader=trader, symbol=symbol, shares_qty=shares_qty).save()
