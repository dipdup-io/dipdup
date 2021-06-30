from datetime import datetime, timezone
import logging
from typing import Any, Dict, List

from aiolimiter import AsyncLimiter
from dipdup.datasources.coinbase.models import CandleData, CandleInterval

from dipdup.datasources.proxy import DatasourceRequestProxy


REST_API_URL = 'https://api.pro.coinbase.com'
WEBSOCKET_API_URL = 'wss://ws-feed.pro.coinbase.com'


class CoinbaseDatasource:
    def __init__(self, cache: bool) -> None:
        self._logger = logging.getLogger('dipdup.coinbase')
        self._proxy = DatasourceRequestProxy(
            cache=cache,
            ratelimiter=AsyncLimiter(max_rate=10, time_period=1),
        )

    async def close_session(self) -> None:
        await self._proxy.close_session()

    async def run(self) -> None:
        pass

    async def resync(self) -> None:
        pass

    async def get_oracle_prices(self) -> Dict[str, Any]:
        return await self._proxy.http_request(
            'get',
            url=f'{REST_API_URL}/oracle',
        )

    async def get_candles(self, since: datetime, until: datetime, interval: CandleInterval, ticker: str = 'XTZ-USD') -> List[CandleData]:
        # TODO: Encapsulate multiple requests
        if (until - since).total_seconds() / interval.value > 300:
            raise Exception('Can\'t request more than 300 candles')

        candles_json = await self._proxy.http_request(
            'get',
            url=f'{REST_API_URL}/products/{ticker}/candles',
            params={
                'start': since.replace(tzinfo=timezone.utc).isoformat(),
                'end': until.replace(tzinfo=timezone.utc).isoformat(),
                'granularity': interval.value,
            }
        )
        return [CandleData.from_json(c) for c in candles_json]
