from decimal import Decimal

from demo_tezos_token_balances import models as models
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosTokenBalanceData


async def on_balance_update(
    ctx: HandlerContext,
    token_balance: TezosTokenBalanceData,
) -> None:
    holder, _ = await models.Holder.get_or_create(address=token_balance.contract_address)
    holder.balance = Decimal(token_balance.balance_value or 0) / (10**8)
    await holder.save()