from typing import Optional, Union
from demo_dex.types.dexter_fa12.storage import DexterFa12Storage

from dipdup.models import OperationData, OperationHandlerContext, OriginationContext, TransactionContext

import demo_dex.models as models

from demo_dex.types.quipuswap_fa12.storage import QuipuswapFa12Storage


async def on_fa12_origination(
    ctx: OperationHandlerContext,
    fa12_origination: OriginationContext[Union[QuipuswapFa12Storage, DexterFa12Storage]],
) -> None:
    if ctx.template_values is None:
        raise Exception('This index must be templated')

    symbol, _ = await models.Symbol.get_or_create(symbol=ctx.template_values['symbol'])

    if isinstance(fa12_origination.storage, QuipuswapFa12Storage):
        for address, ledger in fa12_origination.storage.storage.ledger.items():
            shares_qty = ledger.balance
            trader, _ = await models.Trader.get_or_create(address=address)
            await models.Position(trader=trader, symbol=symbol, shares_qty=shares_qty).save()
    elif isinstance(fa12_origination.storage, DexterFa12Storage):
        for address, account in fa12_origination.storage.accounts.items():
            shares_qty = account.balance
            trader, _ = await models.Trader.get_or_create(address=address)
            await models.Position(trader=trader, symbol=symbol, shares_qty=shares_qty).save()
    else:
        raise NotImplementedError
