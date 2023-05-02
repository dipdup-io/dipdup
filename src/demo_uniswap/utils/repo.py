from collections import OrderedDict
from decimal import Decimal
from typing import Optional
from typing import cast

import demo_uniswap.models as models
from dipdup.config.evm import EvmContractConfig
from dipdup.context import HandlerContext

USDC_WETH_03_POOL = '0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8'


class ModelsRepo:
    def __init__(self) -> None:
        self._factories: OrderedDict[str, models.Factory] = OrderedDict()
        self._pools: OrderedDict[str, models.Pool] = OrderedDict()
        self._tokens: OrderedDict[str, models.Token] = OrderedDict()
        self._positions: OrderedDict[str, models.Position] = OrderedDict()
        self._eth_usd: Optional[Decimal] = None

    async def get_factory(self, factory_address: str) -> models.Factory:
        if factory_address not in self._factories:
            self._pools[factory_address] = await models.Pool.get(id=factory_address)
        return self._factories[factory_address]

    async def update_factory(self, factory: models.Factory) -> None:
        self._factories[factory.id] = factory
        await factory.save()

    async def get_pool(self, pool_address: str) -> models.Pool:
        if pool_address not in self._pools:
            self._pools[pool_address] = await models.Pool.get(id=pool_address)
        return self._pools[pool_address]

    async def update_pool(self, pool: models.Pool) -> None:
        self._pools[pool.id] = pool
        await pool.save()

    async def get_token(self, token_address: str) -> models.Token:
        if token_address not in self._tokens:
            self._tokens[token_address] = await models.Token.get(id=token_address)
        return self._tokens[token_address]

    async def update_tokens(self, *tokens: models.Token) -> None:
        for token in tokens:
            self._tokens[token.id] = token
            await token.save()

    async def get_position(self, token_id: str) -> Optional[models.Position]:
        if token_id not in self._positions:
            position = await models.Position.get_or_none(id=token_id)
            if position is not None:
                self._positions[token_id] = position
            else:
                return None
        return self._positions[token_id]

    async def update_position(self, position: models.Position) -> None:
        self._positions[position.id] = position
        await position.save()

    async def get_eth_usd_rate(self) -> Decimal:
        if self._eth_usd is None:
            try:
                usdc_pool = await self.get_pool(USDC_WETH_03_POOL)
                self._eth_usd = usdc_pool.token0_price
            except Exception:
                return Decimal()
        return self._eth_usd

    def update_eth_usd_rate(self, rate: Decimal) -> None:
        self._eth_usd = rate

    async def get_ctx_factory(self, ctx: HandlerContext) -> models.Factory:
        factory_address = cast(EvmContractConfig, ctx.config.get_contract('factory')).address
        if factory_address is None:
            raise Exception('Factory address is not specified')
        return await self.get_factory(factory_address)


models_repo = ModelsRepo()
