from decimal import Decimal
from typing import Optional

import demo_tzbtc.models as models
from demo_tzbtc.handlers.on_balance_update import on_balance_update
from demo_tzbtc.types.tzbtc.parameter.transfer import TransferParameter
from demo_tzbtc.types.tzbtc.storage import TzbtcStorage
from dipdup.models import OperationData, OperationHandlerContext, Origination, Transaction


async def on_transfer(
    ctx: OperationHandlerContext,
    transfer: Transaction[TransferParameter, TzbtcStorage],
) -> None:
    if transfer.parameter.from_ == transfer.parameter.to:
        return
    amount = Decimal(transfer.parameter.value) / (10 ** 8)
    await on_balance_update(address=transfer.parameter.from_, balance_update=-amount, timestamp=transfer.data.timestamp)
    await on_balance_update(address=transfer.parameter.to, balance_update=amount, timestamp=transfer.data.timestamp)
