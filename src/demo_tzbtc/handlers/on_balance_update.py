from decimal import Decimal
import demo_tzbtc.models as models


async def on_balance_update(address: str, balance_update: Decimal, timestamp: str):
    holder, _ = await models.Holder.get_or_create(address=address)
    holder.balance += balance_update
    holder.turnover += abs(balance_update)
    holder.tx_count += 1
    holder.last_seen = timestamp
    assert holder.balance >= 0, address
    await holder.save()
