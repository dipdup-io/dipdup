from typing import Optional

import demo_quipuswap.models as models
from demo_quipuswap.types.quipu_fa12.storage import QuipuFa12Storage
from dipdup.models import OperationData, OperationHandlerContext, OriginationContext, TransactionContext


async def on_fa12_origination(
    ctx: OperationHandlerContext,
    quipu_fa12_origination: OriginationContext[QuipuFa12Storage],
) -> None:
    if ctx.template_values is None:
        raise Exception('This index must be templated')

    symbol = ctx.template_values['symbol']

    for address, value in quipu_fa12_origination.storage.storage.ledger.items():
        shares_qty = value.balance
        await models.Position(trader=address, symbol=symbol, shares_qty=shares_qty).save()
