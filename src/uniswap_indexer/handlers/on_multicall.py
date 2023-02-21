from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidOperation  # noqa: F401
from uniswap_indexer import models as models  # noqa: F401


async def on_multicall(
    ctx: HandlerContext,
) -> None:
    ...
