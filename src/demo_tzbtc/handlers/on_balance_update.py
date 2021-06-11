from datetime import datetime
from decimal import Decimal

import demo_tzbtc.models as models


async def on_balance_update(address: str, balance_update: Decimal, timestamp: datetime):
    holder, _ = await models.Holder.get_or_create(address=address)
    holder.balance += balance_update  # type: ignore
    holder.turnover += abs(balance_update)  # type: ignore
    holder.tx_count += 1  # type: ignore
    holder.last_seen = timestamp  # type: ignore
    assert holder.balance >= 0, address
    await holder.save()
