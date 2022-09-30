from dipdup.context import HandlerContext
from dipdup.models import Origination

import demo_quipuswap.models as models
from demo_quipuswap.types.quipu_fa12.storage import QuipuFa12Storage


async def on_fa12_origination(
    ctx: HandlerContext,
    quipu_fa12_origination: Origination[QuipuFa12Storage],
) -> None:
    symbol = ctx.template_values['symbol']

    for address, value in quipu_fa12_origination.storage.storage.ledger.items():
        shares_qty = value.balance
        await models.Position(trader=address, symbol=symbol, shares_qty=shares_qty).save()
