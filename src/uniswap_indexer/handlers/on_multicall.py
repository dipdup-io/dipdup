from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidOperation
from uniswap_indexer import models as models


async def on_multicall(
    ctx: HandlerContext,
) -> None:
    ...