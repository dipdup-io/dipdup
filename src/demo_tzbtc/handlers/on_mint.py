from decimal import Decimal

from demo_tzbtc.handlers.on_balance_update import on_balance_update
from demo_tzbtc.types.tzbtc.parameter.mint import MintParameter
from demo_tzbtc.types.tzbtc.storage import TzbtcStorage
from dipdup.context import HandlerContext
from dipdup.models import Transaction


async def on_mint(
    ctx: HandlerContext,
    mint: Transaction[MintParameter, TzbtcStorage],
) -> None:
    amount = Decimal(mint.parameter.value) / (10**8)
    await on_balance_update(address=mint.parameter.to, balance_update=amount, timestamp=mint.data.timestamp)
