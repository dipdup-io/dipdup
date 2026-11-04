from datetime import UTC
from datetime import datetime
from pathlib import Path

from dipdup.config import HttpConfig
from dipdup.config.coinbase import CoinbaseDatasourceConfig
from dipdup.datasources.coinbase import CoinbaseDatasource
from dipdup.models.coinbase import CoinbaseCandleInterval


async def test_coinbase_candles() -> None:
    config = CoinbaseDatasourceConfig(
        kind='coinbase',
        http=HttpConfig(
            replay_path=str(Path(__file__).parent.parent / 'replays'),
        ),
    )
    config._name = 'coinbase'
    coinbase = CoinbaseDatasource(config)
    since = datetime(2026, 10, 1, tzinfo=UTC)
    until = datetime(2026, 10, 2, tzinfo=UTC)

    async with coinbase:
        candles = await coinbase.get_candles(
            since=since,
            until=until,
            interval=CoinbaseCandleInterval.ONE_HOUR,
            ticker='BTC-USD',
        )

    assert len(candles) == 25
    assert candles[0].timestamp == since
    assert candles[-1].timestamp == until
    for candle in candles:
        assert candle.low <= min(candle.open, candle.close)
        assert candle.high >= max(candle.open, candle.close)
