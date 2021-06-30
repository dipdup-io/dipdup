from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Union

from pydantic.dataclasses import dataclass


class CandleInterval(Enum):
    ONE_MINUTE = 60
    FIVE_MINUTES = 300
    FIFTEEN_MINUTES = 900
    ONE_HOUR = 3600
    SIX_HOURS = 21600
    ONE_DAY = 86400


@dataclass
class CandleData:
    timestamp: datetime
    low: Decimal
    high: Decimal
    open: Decimal
    close: Decimal
    volume: Decimal

    @classmethod
    def from_json(cls, json: List[Union[int, float]]) -> 'CandleData':
        return CandleData(
            timestamp=datetime.fromtimestamp(json[0], tz=timezone.utc),
            low=Decimal(str(json[1])),
            high=Decimal(str(json[2])),
            open=Decimal(str(json[3])),
            close=Decimal(str(json[4])),
            volume=Decimal(str(json[5])),
        )
