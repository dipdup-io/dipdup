from dipdup.context import HandlerContext
from dipdup.models.evm import EvmLog

from demo_evm_uniswap import models
from demo_evm_uniswap.models.repo import get_ctx_factory
from demo_evm_uniswap.models.repo import models_repo
from demo_evm_uniswap.models.tick import tick_get_or_create
from demo_evm_uniswap.models.token import convert_token_amount
from demo_evm_uniswap.types.pool.evm_logs.burn import BurnPayload
from demo_evm_uniswap.types.pool.evm_logs.mint import MintPayload


class PoolUpdateSign:
    MINT = 1
    BURN = -1


async def pool_update(
    ctx: HandlerContext,
    pool: models.Pool,
    log: EvmLog[BurnPayload] | EvmLog[MintPayload],
    sign: int,
) -> None:
    factory = await get_ctx_factory(ctx)
    token0 = await models.Token.cached_get(pool.token0_id)
    token1 = await models.Token.cached_get(pool.token1_id)

    amount0 = convert_token_amount(log.payload.amount0, token0.decimals)
    amount1 = convert_token_amount(log.payload.amount1, token1.decimals)

    eth_usd = await models_repo.get_eth_usd_rate()
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
    await token0.save()
    await token1.save()

    pool.tx_count += 1

    if pool.tick is not None and log.payload.tickLower < pool.tick < log.payload.tickUpper:
        pool.liquidity = pool.liquidity + sign * log.payload.amount

    pool.total_value_locked_token0 = pool.total_value_locked_token0 + sign * amount0
    pool.total_value_locked_token1 = pool.total_value_locked_token1 + sign * amount1
    pool.total_value_locked_eth = (
        pool.total_value_locked_token0 * token0.derived_eth + pool.total_value_locked_token1 * token1.derived_eth
    )
    pool.total_value_locked_usd = pool.total_value_locked_eth * eth_usd
    await pool.save()

    factory.total_value_locked_eth = factory.total_value_locked_eth + sign * pool.total_value_locked_eth
    factory.total_value_locked_usd = factory.total_value_locked_eth * eth_usd
    await factory.save()

    tx_defaults = {
        'id': f'{log.data.transaction_hash}#{log.data.log_index}',
        'transaction_hash': log.data.transaction_hash,
        'timestamp': 0,  # FIXME
        'pool': pool,
        'token0': token0,
        'token1': token1,
        'owner': log.payload.owner,
        'amount': log.payload.amount,
        'amount0': amount0,
        'amount1': amount1,
        'amount_usd': amount_usd,
        'tick_lower': log.payload.tickLower,
        'tick_upper': log.payload.tickUpper,
        'log_index': log.data.log_index,
    }

    tx: models.Burn | models.Mint
    if isinstance(log.payload, MintPayload) and sign == PoolUpdateSign.MINT:
        if not isinstance(log.payload, MintPayload):
            raise Exception('Invalid event type')
        tx = models.Mint(sender=log.payload.sender, **tx_defaults)
    elif isinstance(log.payload, BurnPayload) and sign == PoolUpdateSign.BURN:
        tx = models.Burn(**tx_defaults)
    else:
        raise Exception('Invalid event type')
    await tx.save()

    lower_tick = await tick_get_or_create(log.payload.tickLower, pool, log.data.level, log.data.timestamp)
    lower_tick.liquidity_gross = lower_tick.liquidity_gross + sign * log.payload.amount
    lower_tick.liquidity_net = lower_tick.liquidity_net + sign * log.payload.amount
    await lower_tick.save()

    upper_tick = await tick_get_or_create(log.payload.tickUpper, pool, log.data.level, log.data.timestamp)
    upper_tick.liquidity_gross = upper_tick.liquidity_gross + sign * log.payload.amount
    upper_tick.liquidity_net = upper_tick.liquidity_net - sign * log.payload.amount
    await upper_tick.save()