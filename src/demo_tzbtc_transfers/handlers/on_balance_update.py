from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation

import demo_tzbtc_transfers.models as models


async def on_balance_update(address: str, balance_update: Decimal, timestamp: datetime):
    try:
        holder, _ = await models.Holder.get_or_create(address=address)
        holder.balance += balance_update  # type: ignore
        holder.turnover += abs(balance_update)  # type: ignore
        holder.tx_count += 1  # type: ignore
        holder.last_seen = timestamp  # type: ignore
        await holder.save()
    except InvalidOperation:
        return
