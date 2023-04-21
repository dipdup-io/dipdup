from demo_uniswap.utils.repo import models_repo
from demo_uniswap.types.pool.evm_events.initialize import Initialize
from demo_uniswap.utils.token import token_derive_eth
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent


async def initialize(
    ctx: HandlerContext,
    event: SubsquidEvent[Initialize],
) -> None:
    pool = await models_repo.get_pool(event.data.address)
    pool.sqrt_price = event.payload.sqrtPriceX96
    pool.tick = event.payload.tick
    await models_repo.update_pool(pool)

    token0 = await models_repo.get_token(pool.token0)
    token1 = await models_repo.get_token(pool.token1)
    token0.derived_eth = token_derive_eth(token0)
    token1.derived_eth = token_derive_eth(token1)
    await models_repo.update_tokens(token0, token1)
