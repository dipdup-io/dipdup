from typing import Optional
from decimal import Decimal

from dipdup.models import OperationData, OperationHandlerContext, OriginationContext, TransactionContext

import demo_tzbtc.models as models

from demo_tzbtc.types.tzbtc.parameter.mint import MintParameter
from demo_tzbtc.types.tzbtc.storage import TzbtcStorage
from demo_tzbtc.handlers.on_balance_update import on_balance_update


async def on_mint(
    ctx: OperationHandlerContext,
    mint: TransactionContext[MintParameter, TzbtcStorage],
) -> None:
    amount = Decimal(mint.parameter.value) / (10 ** 8)
    await on_balance_update(address=mint.parameter.to,
                            balance_update=amount,
                            timestamp=mint.data.timestamp)
