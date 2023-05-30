from decimal import Decimal
from typing import cast, Dict, Any

from lru import LRU

import demo_uniswap.models as models
from dipdup.config.evm import EvmContractConfig
from dipdup.context import HandlerContext

USDC_WETH_03_POOL = '0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8'


class ModelsRepo:
    def __init__(self) -> None:
        self._eth_usd: Decimal | None = None
        self._pending_positions = LRU(4096)

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

    def save_pending_position(self, idx: str, position: Dict[str, Any]) -> None:
        self._pending_positions[idx] = position

    def get_pending_position(self, idx: str) -> Dict[str, Any]:
        res = self._pending_positions.get(idx, None)
        if res is None:
            raise ValueError(f'Failed to find pending position {idx}')
        return cast(Dict[str, Any], res)


async def get_ctx_factory(ctx: HandlerContext) -> models.Factory:
    factory_address = cast(EvmContractConfig, ctx.config.get_contract('factory')).address
    if factory_address is None:
        raise Exception('Factory address is not specified')
    return await models.Factory.cached_get(factory_address)


models_repo = ModelsRepo()
