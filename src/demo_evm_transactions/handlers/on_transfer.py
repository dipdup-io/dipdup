from decimal import Decimal

from demo_evm_transactions import models as models
from demo_evm_transactions.types.eth_usdt.evm_transactions.transfer import TransferInput
from dipdup.context import HandlerContext
from dipdup.models.evm import EvmTransaction
from tortoise.exceptions import DoesNotExist


async def on_transfer(
    ctx: HandlerContext,
    transaction: EvmTransaction[TransferInput],
) -> None:
    amount = Decimal(transaction.input.value) / (10**6)
    if not amount:
        return

    await on_balance_update(
        address=transaction.data.from_,
        balance_update=-amount,
        level=transaction.data.level,
    )
    await on_balance_update(
        address=transaction.input.to,
        balance_update=amount,
        level=transaction.data.level,
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