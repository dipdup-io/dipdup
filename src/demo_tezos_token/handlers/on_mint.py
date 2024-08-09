from decimal import Decimal

from demo_tezos_token.handlers.on_balance_update import on_balance_update
from demo_tezos_token.types.tzbtc.tezos_parameters.mint import MintParameter
from demo_tezos_token.types.tzbtc.tezos_storage import TzbtcStorage
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosTransaction


async def on_mint(
    ctx: HandlerContext,
    mint: TezosTransaction[MintParameter, TzbtcStorage],
) -> None:
    amount = Decimal(mint.parameter.value) / (10**8)
    await on_balance_update(
        address=mint.parameter.to,
        balance_update=amount,
        timestamp=mint.data.timestamp,
    )
