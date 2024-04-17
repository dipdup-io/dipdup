from decimal import Decimal

from demo_evm_logs import models as models
from demo_evm_logs.types.eth_usdt.evm_logs.transfer import TransferPayload
from dipdup.context import HandlerContext
from dipdup.models.evm import EvmLog
from tortoise.exceptions import DoesNotExist


async def on_transfer(
    ctx: HandlerContext,
    log: EvmLog[TransferPayload],
) -> None:
    amount = Decimal(log.payload.value) / (10**6)
    if not amount:
        return

    await on_balance_update(
        address=log.payload.from_,
        balance_update=-amount,
        level=log.data.level,
    )
    await on_balance_update(
        address=log.payload.to,
        balance_update=amount,
        level=log.data.level,
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