from contextlib import suppress
from typing import cast

from demo_uniswap import models as models
from demo_uniswap.models.token import WHITELIST_TOKENS
from demo_uniswap.models.token import ERC20Token
from demo_uniswap.types.factory.evm_events.pool_created import PoolCreated
from dipdup.config.evm import EvmContractConfig
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent
from tortoise.exceptions import OperationalError

POOL_BLACKLIST = {'0x8fe8d9bb8eeba3ed688069c3d6b556c9ca258248'}
WETH_ADDRESS = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'


async def create_token(ctx: HandlerContext, address: str, pool_id: str) -> None:
    with suppress(Exception):
        await models.Token.cached_get(address)
        return

    web3 = ctx.get_evm_node_datasource('subsquid').web3
    erc20_iface = ERC20Token.from_address(web3, address)
    token = models.Token(
        id=address,
        symbol=await erc20_iface.get_symbol(),
        name=await erc20_iface.get_name(),
        decimals=await erc20_iface.get_decimals(),
        total_supply=await erc20_iface.get_total_supply(),
        derived_eth=1 if address == WETH_ADDRESS else 0,
        whitelist_pools=[pool_id] if address in WHITELIST_TOKENS else [],
    )
    token.cache()
    await token.save()


async def pool_created(
    ctx: HandlerContext,
    event: SubsquidEvent[PoolCreated],
) -> None:
    if event.payload.pool in POOL_BLACKLIST:
        ctx.logger.info('Pool %s is blacklisted', event.payload.pool)
        return

    factory_address = cast(EvmContractConfig, ctx.config.get_contract('factory')).address
    factory, _ = await models.Factory.get_or_create(id=factory_address)
    factory.pool_count += 1
    await factory.save()

    pool_id = event.payload.pool
    try:
        token0 = event.payload.token0
        await create_token(ctx, token0, pool_id)
    except Exception as e:
        ctx.logger.warning('Failed to get token %s for pool %s: %s', token0, pool_id, e)
        return  # skip this pool
    try:
        token1 = event.payload.token1
        await create_token(ctx, token1, pool_id)
    except Exception as e:
        ctx.logger.warning('Failed to get token %s for pool %s: %s', token1, pool_id, e)
        return  # skip this pool

    pool = models.Pool(
        id=pool_id,
        fee_tier=int(event.payload.fee),
        created_at_timestamp=event.data.timestamp,
        created_at_block_number=int(event.data.level),
        token0_id=token0,
        token1_id=token1,
    )
    # NOTE: Could present after wipe with immune_tables
    with suppress(OperationalError):
        await pool.save()
        pool.cache()