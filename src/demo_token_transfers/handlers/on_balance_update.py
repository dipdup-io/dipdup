from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation

import demo_token_transfers.models as models


async def on_balance_update(address: str, balance_update: Decimal, timestamp: datetime) -> None:
    try:
        holder, _ = await models.Holder.get_or_create(address=address)
        holder.balance += balance_update
        holder.turnover += abs(balance_update)
        holder.tx_count += 1
        holder.last_seen = timestamp
        await holder.save()
    except InvalidOperation:
        return