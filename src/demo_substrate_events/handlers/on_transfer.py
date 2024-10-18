from decimal import Decimal

from tortoise.exceptions import DoesNotExist

from demo_substrate_events import models as models
from demo_substrate_events.types.assethub.substrate_events.assets_transferred import AssetsTransferredPayload
from dipdup.context import HandlerContext
from dipdup.models.substrate import SubstrateEvent


async def on_transfer(
    ctx: HandlerContext,
    event: SubstrateEvent[AssetsTransferredPayload],
) -> None:
    amount = Decimal(event.payload.get('amount') or event.payload['value'])
    if not amount:
        return

    address_from = event.payload['from']
    await on_balance_update(
        address=address_from,
        balance_update=-amount,
        level=event.data.level,
    )
    address_to = event.payload['to']
    await on_balance_update(
        address=address_to,
        balance_update=amount,
        level=event.data.level,
    )


async def on_balance_update(
    address: str,
    balance_update: Decimal,
    level: int,
) -> None:
    try:
        holder = await models.Holder.cached_get(pk=address)
    except DoesNotExist:
        holder = models.Holder(
            address=address,
            balance=0,
            turnover=0,
            tx_count=0,
            last_seen=None,
        )
        holder.cache()
    holder.balance += balance_update
    holder.turnover += abs(balance_update)
    holder.tx_count += 1
    holder.last_seen = level
    await holder.save()