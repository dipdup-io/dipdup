from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent  # noqa: F401
from uniswap_indexer import models as models  # noqa: F401

# from uniswap_indexer.types.uniswap_v3_router.event.new_trade import NewTradePayload


async def on_new_trade(
    ctx: HandlerContext,
    # event: SubsquidEvent[NewTradePayload],
) -> None:
    ...
