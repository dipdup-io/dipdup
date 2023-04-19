from demo_uniswap import models as models
from demo_uniswap.types.factory.evm_events.pool_created import PoolCreated
from dipdup.config.evm_node import EvmNodeDatasourceConfig
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent
from dipdup.config.evm import EvmContractConfig
from demo_uniswap.utils.token import ERC20Token
from typing import cast

POOL_BLACKLIST = {'0x8fe8d9bb8eeba3ed688069c3d6b556c9ca258248'}


async def token_get_or_create(ctx: HandlerContext, address: str | bytes) -> models.Token:
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
        )
    return token


async def pool_created(
    ctx: HandlerContext,
    event: SubsquidEvent[PoolCreated],
) -> None:
    if event.payload.pool in POOL_BLACKLIST:
        return

    factory_address = cast(EvmContractConfig, ctx.config.get_contract('factory')).address
    factory, _ = await models.Factory.get_or_create(id=factory_address)
    factory.pool_count += 1

    try:
        token0 = await token_get_or_create(ctx, event.payload.token0)
        token1 = await token_get_or_create(ctx, event.payload.token1)
    except ValueError:
        return
    else:
        await token0.save()
        await token1.save()

    pool = models.Pool(
        id=event.payload.pool,
        fee_tier=int(event.payload.fee),
        created_at_timestamp=int(0),  # TODO: get block (head) time by level
        created_at_block_number=int(event.data.level),
        token0=token0,
        token1=token1,
    )

    await pool.save()
    await factory.save()
