from eth_utils.address import to_checksum_address
from eth_utils.address import to_normalized_address

import demo_uniswap.models as models
from demo_uniswap.utils.abi import get_abi
from dipdup.context import HandlerContext

position_manager_abi = get_abi('position_manager_abi.abi')
factory_abi = get_abi('factory_abi.abi')

_positions: dict[int, models.Position | None] = {}


async def position_get_or_create(ctx: HandlerContext, contract_address: str, token_id: int) -> models.Position | None:
    if token_id in _positions:
        return _positions[token_id]

    position = await models.Position.get_or_none(id=token_id)
    if position:
        _positions[token_id] = position
        return position

    web3 = ctx.get_evm_node_datasource('mainnet_node').web3
    manager = web3.eth.contract(address=to_checksum_address(contract_address), abi=position_manager_abi)

    try:
        # nonce uint96,
        # operator address,
        # token0 address,
        # token1 address,
        # fee uint24,
        # tickLower int24,
        # tickUpper int24,
        # liquidity uint128,
        # feeGrowthInside0LastX128 uint256,
        # feeGrowthInside1LastX128 uint256,
        # tokensOwed0 uint128,
        # tokensOwed1 uint128
        response = await manager.functions.positions(token_id).call()
        _, _, token0, token1, fee, tick_lower, tick_upper, _, _, _, _, _ = response
    except Exception as e:
        ctx.logger.debug('Failed to eth_call %s with param %d: %s', contract_address, token_id, str(e))
        _positions[token_id] = None
        return None

    factory_address = ctx.config.get_contract('factory').address  # type: ignore[attr-defined]
    factory = web3.eth.contract(address=to_checksum_address(factory_address), abi=factory_abi)

    try:
        pool_address = await factory.functions.getPool(token0, token1, fee).call()
    except Exception as e:
        ctx.logger.debug('Failed to eth_call %s with param %s: %s', factory_address, str(token0, token1, fee), str(e))
        _positions[token_id] = None
        return None

    pool_address = to_normalized_address(pool_address)

    if not await models.Pool.cached_get_or_none(pool_address):
        _positions[token_id] = None
        return None

    position = models.Position(
        id=token_id,
        pool_id=pool_address,
        token0_id=to_normalized_address(token0),
        token1_id=to_normalized_address(token1),
        # tick_lower_id=f'{pool_address}#{tick_lower}',
        # tick_upper_id=f'{pool_address}#{tick_upper}'
    )
    await position.save()
    _positions[token_id] = position
    return position


async def save_position_snapshot(position: models.Position, level: int) -> None:
    snapshot, exists = await models.PositionSnapshot.get_or_create(
        id=f'{position.id}#{level}',
        defaults={
            'owner': position.owner,
            'pool_id': position.pool_id,
            'position_id': position.id,
            'block_number': level,
            'timestamp': 0,  # TODO:
        },
    )  # TODO: less i/o
    snapshot.liquidity = position.liquidity
    snapshot.deposited_token0 = position.deposited_token0
    snapshot.deposited_token1 = position.deposited_token1
    snapshot.withdrawn_token0 = position.withdrawn_token0
    snapshot.withdrawn_token1 = position.withdrawn_token1
    snapshot.collected_fees_token0 = position.collected_fees_token0
    snapshot.collected_fees_token1 = position.collected_fees_token1
    await snapshot.save()
