from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any

from dipdup.config import HttpConfig
from dipdup.config.coinbase import CoinbaseDatasourceConfig
from dipdup.datasources import Datasource
from dipdup.exceptions import UnsupportedFeatureError
from dipdup.models.coinbase import CoinbaseCandleData
from dipdup.models.coinbase import CoinbaseCandleInterval

CANDLES_REQUEST_LIMIT = 300


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
        """Always raises `UnsupportedFeatureError`: Coinbase has retired its Price Oracle API."""
        raise UnsupportedFeatureError(
            'Coinbase deprecated its Price Oracle API on 2025-01-01, so `get_oracle_prices` has no endpoint to call. '
            'See https://docs.cdp.coinbase.com/exchange/changes/changelog'
        )

    async def get_candles(
        self,
        since: datetime,
        until: datetime,
        interval: CoinbaseCandleInterval,
        ticker: str,
    ) -> list[CoinbaseCandleData]:
        # NOTE: Pages share a boundary and Coinbase includes both `start` and `end`, so a candle can come twice.
        candles: dict[datetime, CoinbaseCandleData] = {}
        for _since, _until in self._split_candle_requests(since, until, interval):
            candles_json = await self.request(
                'get',
                url=f'products/{ticker}/candles',
                params={
                    'start': _since.replace(tzinfo=UTC).isoformat(),
                    'end': _until.replace(tzinfo=UTC).isoformat(),
                    'granularity': interval.seconds,
                },
            )
            for candle_json in candles_json:
                candle = CoinbaseCandleData.from_json(candle_json)
                candles[candle.timestamp] = candle
        return sorted(candles.values(), key=lambda c: c.timestamp)

    def _split_candle_requests(
        self,
        since: datetime,
        until: datetime,
        interval: CoinbaseCandleInterval,
    ) -> list[tuple[datetime, datetime]]:
        request_interval_limit = timedelta(seconds=interval.seconds * CANDLES_REQUEST_LIMIT)
        request_intervals = []
        while since + request_interval_limit < until:
            request_intervals.append((since, since + request_interval_limit))
            since += request_interval_limit
        request_intervals.append((since, until))
        return request_intervals
