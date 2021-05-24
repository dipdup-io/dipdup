from typing import Optional

from dipdup.models import OperationData, OperationHandlerContext, OriginationContext, TransactionContext

import demo_quipuswap_dexter.models as models

from demo_quipuswap_dexter.types.quipuswap_fa2_ptai.storage import QuipuswapFa2PtaiStorage


async def on_fa2_origination(
    ctx: OperationHandlerContext,
    quipuswap_fa2_origination: OriginationContext[QuipuswapFa2PtaiStorage],
) -> None:
    if ctx.template_values is None:
        raise Exception('This index must be templated')

    symbol, _ = await models.Symbol.get_or_create(symbol=ctx.template_values['symbol'])

    for address, value in quipuswap_fa2_origination.storage.storage.ledger.items():
        shares_qty = value.balance
        trader, _ = await models.Trader.get_or_create(address=address)
        await models.Position(trader=trader, symbol=symbol, shares_qty=shares_qty).save()
