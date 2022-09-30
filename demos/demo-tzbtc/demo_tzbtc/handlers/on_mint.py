
from dipdup.models import Transaction
from demo_tzbtc.types.tzbtc.storage import TzbtcStorage
from demo_tzbtc.types.tzbtc.parameter.mint import MintParameter
from dipdup.context import HandlerContext

async def on_mint(
    ctx: HandlerContext,
    mint: Transaction[MintParameter, TzbtcStorage],
) -> None:
    ...