from datetime import UTC
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic.dataclasses import dataclass


class CoinbaseCandleInterval(Enum):
    ONE_MINUTE = 'ONE_MINUTE'
    FIVE_MINUTES = 'FIVE_MINUTES'
    FIFTEEN_MINUTES = 'FIFTEEN_MINUTES'
    ONE_HOUR = 'ONE_HOUR'
    SIX_HOURS = 'SIX_HOURS'
    ONE_DAY = 'ONE_DAY'

    @property
    def seconds(self) -> int:
        return {
            CoinbaseCandleInterval.ONE_MINUTE: 60,
            CoinbaseCandleInterval.FIVE_MINUTES: 300,
            CoinbaseCandleInterval.FIFTEEN_MINUTES: 900,
            CoinbaseCandleInterval.ONE_HOUR: 3600,
            CoinbaseCandleInterval.SIX_HOURS: 21600,
            CoinbaseCandleInterval.ONE_DAY: 86400,
        }[self]


@dataclass
class CoinbaseCandleData:
    timestamp: datetime
    low: Decimal
    high: Decimal
    open: Decimal
    close: Decimal
    volume: Decimal

    @classmethod
    def from_json(cls, json: list[int | float]) -> 'CoinbaseCandleData':
        return CoinbaseCandleData(
            timestamp=datetime.fromtimestamp(json[0], tz=UTC),
            low=Decimal(str(json[1])),
            high=Decimal(str(json[2])),
            open=Decimal(str(json[3])),
            close=Decimal(str(json[4])),
            volume=Decimal(str(json[5])),
        )
