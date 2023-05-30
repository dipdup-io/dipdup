from decimal import Decimal
from typing import cast

import demo_uniswap.models as models
from dipdup.config.evm import EvmContractConfig
from dipdup.context import HandlerContext

USDC_WETH_03_POOL = '0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8'


class ModelsRepo:
    def __init__(self) -> None:
        self._eth_usd: Decimal | None = None
        self._next_position_id: int | None = None

    async def get_eth_usd_rate(self) -> Decimal:
        if self._eth_usd is None:
            try:
                usdc_pool = await models.Pool.cached_get(USDC_WETH_03_POOL)
                self._eth_usd = usdc_pool.token0_price
            except Exception:
                return Decimal()
        return self._eth_usd

    def update_eth_usd_rate(self, rate: Decimal) -> None:
        self._eth_usd = rate

    async def get_next_position_id(self) -> int:
        if self._next_position_id is None:
            position = await models.Position.all().order_by('-id').first()
            self._next_position_id = 0 if position is None else position.id
        self._next_position_id += 1
        return self._next_position_id


async def get_ctx_factory(ctx: HandlerContext) -> models.Factory:
    factory_address = cast(EvmContractConfig, ctx.config.get_contract('factory')).address
    if factory_address is None:
        raise Exception('Factory address is not specified')
    return await models.Factory.cached_get(factory_address)


models_repo = ModelsRepo()
