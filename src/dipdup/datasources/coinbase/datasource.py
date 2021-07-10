import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from dipdup.config import HTTPConfig
from dipdup.datasources.coinbase.models import CandleData, CandleInterval
from dipdup.datasources.proxy import HTTPRequestProxy

CANDLES_REQUEST_LIMIT = 300
REST_API_URL = 'https://api.pro.coinbase.com'
WEBSOCKET_API_URL = 'wss://ws-feed.pro.coinbase.com'


class CoinbaseDatasource:
    def __init__(self, http_config: Optional[HTTPConfig] = None) -> None:
        if http_config is None:
            http_config = HTTPConfig(
                cache=True,
                ratelimit_rate=10,
                ratelimit_period=1,
            )

        self._logger = logging.getLogger('dipdup.coinbase')
        self._proxy = HTTPRequestProxy(http_config)

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
        candles = []
        for _since, _until in self._split_candle_requests(since, until, interval):
            candles_json = await self._proxy.http_request(
                'get',
                url=f'{REST_API_URL}/products/{ticker}/candles',
                params={
                    'start': _since.replace(tzinfo=timezone.utc).isoformat(),
                    'end': _until.replace(tzinfo=timezone.utc).isoformat(),
                    'granularity': interval.seconds,
                },
                cache=True,
            )
            candles += [CandleData.from_json(c) for c in candles_json]
        return sorted(candles, key=lambda c: c.timestamp)

    def _split_candle_requests(self, since: datetime, until: datetime, interval: CandleInterval) -> List[Tuple[datetime, datetime]]:
        request_interval_limit = timedelta(seconds=interval.seconds * CANDLES_REQUEST_LIMIT)
        request_intervals = []
        while since + request_interval_limit < until:
            request_intervals.append((since, since + request_interval_limit))
            since += request_interval_limit
        request_intervals.append((since, until))
        return request_intervals
