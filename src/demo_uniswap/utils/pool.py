from demo_uniswap import models
from demo_uniswap.utils.repo import models_repo
from demo_uniswap.utils.token import convert_token_amount
from demo_uniswap.utils.tick import tick_get_or_create
from demo_uniswap.types.pool.evm_events.burn import Burn
from demo_uniswap.types.pool.evm_events.mint import Mint
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent
from typing import Union


class PoolUpdateSign:
    MINT = 1
    BURN = -1


async def pool_update(
    ctx: HandlerContext,
    event: SubsquidEvent[Union[Burn, Mint]],
    sign: int
) -> None:
    factory = await models_repo.get_ctx_factory(ctx)
    pool = await models_repo.get_pool(event.data.address)
    token0 = await models_repo.get_token(pool.token0)
    token1 = await models_repo.get_token(pool.token1)

    amount0 = convert_token_amount(event.payload.amount0, token0.decimals)
    amount1 = convert_token_amount(event.payload.amount1, token1.decimals)

    eth_usd = models_repo.get_eth_usd_rate()
    amount_usd = (amount0 * token0.derived_eth + amount1 * token1.derived_eth) * eth_usd

    # reset tvl aggregates until new amounts calculated
    factory.total_value_locked_eth -= pool.total_value_locked_eth
    # update globals
    factory.tx_count += 1

    token0.tx_count += 1
    token0.total_value_locked = token0.total_value_locked + sign * amount0
    token0.total_value_locked_usd = token0.total_value_locked * token0.derived_eth * eth_usd

    token1.tx_count += 1
    token1.total_value_locked = token1.total_value_locked + sign * amount1
    token1.total_value_locked_usd = token1.total_value_locked * token1.derived_eth * eth_usd
    await models_repo.update_tokens(token0, token1)

    pool.tx_count += 1

    if pool.tick is not None \
            and event.payload.tickLower < pool.tick < event.payload.tickUpper:
        pool.liquidity = pool.liquidity + sign * event.payload.amount

    pool.total_value_locked_token0 = pool.total_value_locked_token0 + sign * amount0
    pool.total_value_locked_token1 = pool.total_value_locked_token1 + sign * amount1
    pool.total_value_locked_eth = pool.total_value_locked_token0 * token0.derived_eth \
        + pool.total_value_locked_token1 * token1.derived_eth
    pool.total_value_locked_usd = pool.total_value_locked_eth * eth_usd
    await models_repo.update_pool(pool)

    factory.total_value_locked_eth = factory.total_value_locked_eth + sign * pool.total_value_locked_eth
    factory.total_value_locked_usd = factory.total_value_locked_eth * eth_usd
    await models_repo.update_factory(factory)

    tx_defaults = dict(
        id=f'{event.data.transaction_hash}#{pool.tx_count}',
        transaction_hash=event.data.transaction_hash,
        pool=pool,
        token0=token0,
        token1=token1,
        owner=event.payload.owner,
        amount=event.payload.amount,
        amount0=amount0,
        amount1=amount1,
        amount_usd=amount_usd,
        tick_lower=event.payload.tickLower,
        tick_upper=event.payload.tickUpper,
        log_index=event.data.index
    )

    if sign == PoolUpdateSign.MINT:
        tx = models.Mint(sender=event.payload.sender, **tx_defaults)
    else:
        tx = models.Burn(**tx_defaults)
    await tx.save()

    lower_tick = await tick_get_or_create(event.payload.tickLower, pool, event.data.level)
    lower_tick.liquidity_gross = lower_tick.liquidity_gross + sign * event.payload.amount
    lower_tick.liquidity_net = lower_tick.liquidity_net + sign * event.payload.amount
    await lower_tick.save()

    upper_tick = await tick_get_or_create(event.payload.tickUpper, pool, event.data.level)
    upper_tick.liquidity_gross = upper_tick.liquidity_gross + sign * event.payload.amount
    upper_tick.liquidity_net = upper_tick.liquidity_net - sign * event.payload.amount
    await upper_tick.save()
