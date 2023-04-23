from demo_uniswap import models as models
from demo_uniswap.types.factory.evm_events.pool_created import PoolCreated
from dipdup.config.evm_node import EvmNodeDatasourceConfig
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent
from dipdup.config.evm import EvmContractConfig
from demo_uniswap.utils.token import ERC20Token, WHITELIST_TOKENS
from demo_uniswap.utils.repo import models_repo
from typing import cast, Set

POOL_BLACKLIST = {'0x8fe8d9bb8eeba3ed688069c3d6b556c9ca258248'}
WETH_ADDRESS = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'


async def token_get_or_create(ctx: HandlerContext, address: str, pool_id: str) -> models.Token:
    token = await models.Token.get_or_none(id=address)
    if token is None:
        ds = cast(EvmNodeDatasourceConfig, ctx.config.get_datasource('mainnet_node'))
        erc20_iface = ERC20Token.from_address(address, ds.url)
        token = models.Token(
            id=address,
            symbol=erc20_iface.get_symbol(),
            name=erc20_iface.get_name(),
            decimals=erc20_iface.get_decimals(),
            total_supply=erc20_iface.get_total_supply(),
            derived_eth=1 if address == WETH_ADDRESS else 0,
            whitelist_pools=[pool_id] if address in WHITELIST_TOKENS else [],
        )
    return token


async def pool_created(
    ctx: HandlerContext,
    event: SubsquidEvent[PoolCreated],
) -> None:
    if event.payload.pool in POOL_BLACKLIST:
        ctx.logger.debug('Pool %s is blacklisted', event.payload.pool)
        return

    factory_address = cast(EvmContractConfig, ctx.config.get_contract('factory')).address
    factory, _ = await models.Factory.get_or_create(id=factory_address)
    factory.pool_count += 1
    await models_repo.update_factory(factory)

    try:
        token0 = await token_get_or_create(ctx, event.payload.token0, event.payload.pool)
        token1 = await token_get_or_create(ctx, event.payload.token1, event.payload.pool)
    except ValueError:
        ctx.logger.debug('Failed to get tokens (%s, %s) for pool %s', event.payload.token0, event.payload.token1, event.payload.pool)
        return  # skip this pool
    else:
        await models_repo.update_tokens(token0, token1)

    pool = models.Pool(
        id=event.payload.pool,
        fee_tier=int(event.payload.fee),
        created_at_timestamp=int(0),  # TODO: get block (head) time by level
        created_at_block_number=int(event.data.level),
        token0_id=event.payload.token0,
        token1_id=event.payload.token1,
    )
    await models_repo.update_pool(pool)

    name = f'{token0.symbol.lower()}_{token1.symbol.lower()}#{pool.id[-6:]}'
    await ctx.add_contract(
        name=name,
        address=pool.id,
        typename='pool',
        kind='evm',
    )
    await ctx.add_index(
        name=f'pool#{name}',
        template='uniswap_v3_pool',
        values=dict(
            datasource=ctx.datasource.name,
            pool=name
        ),
        first_level=event.data.level - 1,  # FIXME: ?
    )
