from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import cast

from dipdup.config import HttpConfig
from dipdup.config.coinbase import CoinbaseDatasourceConfig
from dipdup.datasources import Datasource
from dipdup.models.coinbase import CandleData
from dipdup.models.coinbase import CandleInterval

CANDLES_REQUEST_LIMIT = 300
API_URL = 'https://api.pro.coinbase.com'


class CoinbaseDatasource(Datasource[CoinbaseDatasourceConfig]):
    _default_http_config = HttpConfig(
        retry_sleep=1,
        retry_multiplier=1.1,
        ratelimit_rate=10,
        ratelimit_period=1,
    )

    async def run(self) -> None:
        pass

    async def get_oracle_prices(self) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self.request(
                'get',
                url='oracle',
            ),
        )

    async def get_candles(
        self,
        since: datetime,
        until: datetime,
        interval: CandleInterval,
        ticker: str,
    ) -> list[CandleData]:
        candles = []
        for _since, _until in self._split_candle_requests(since, until, interval):
            candles_json = await self.request(
                'get',
                url=f'products/{ticker}/candles',
                params={
                    'start': _since.replace(tzinfo=timezone.utc).isoformat(),
                    'end': _until.replace(tzinfo=timezone.utc).isoformat(),
                    'granularity': interval.seconds,
                },
            )
            candles += [CandleData.from_json(c) for c in candles_json]
        return sorted(candles, key=lambda c: c.timestamp)

    def _split_candle_requests(
        self,
        since: datetime,
        until: datetime,
        interval: CandleInterval,
    ) -> list[tuple[datetime, datetime]]:
        request_interval_limit = timedelta(seconds=interval.seconds * CANDLES_REQUEST_LIMIT)
        request_intervals = []
        while since + request_interval_limit < until:
            request_intervals.append((since, since + request_interval_limit))
            since += request_interval_limit
        request_intervals.append((since, until))
        return request_intervals
