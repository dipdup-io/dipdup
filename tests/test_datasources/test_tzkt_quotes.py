import json
from decimal import Decimal

import pytest

from dipdup.models.tezos_tzkt import TzktQuoteData


@pytest.mark.parametrize(
    'tzkt_quote_json, expected_fields',
    [
        [
            '{"level":2706800,"timestamp":"2022-09-13T14:10:59Z","btc":7.430321914172931E-05,"eur":1.5702972861340734,"usd":1.5734678237990354,"cny":10.896894066937795,"jpy":226.8776313310482,"krw":2192.5289432740697,"eth":0.000982514979977172,"gbp":1.3628685963904752}',
            {
                'level': 2706800,
                'btc': Decimal('0.0000743032191417293'),
                'eur': Decimal('1.570297286134073'),
                'usd': Decimal('1.573467823799035'),
                'cny': Decimal('10.89689406693779'),
                'jpy': Decimal('226.877631331048'),
                'krw': Decimal('2192.528943274069'),
                'eth': Decimal('0.00098251497997717'),
                'gbp': Decimal('1.362868596390475'),
            },
        ]
    ],
)
async def test_convert_quote(tzkt_quote_json: str, expected_fields: dict[str, object]) -> None:
    tzkt_quote_dict = json.loads(tzkt_quote_json)
    quote = TzktQuoteData.from_json(tzkt_quote_dict)
    assert quote
    assert isinstance(quote, TzktQuoteData)
    for field, expected_value in expected_fields.items():
        assert hasattr(quote, field)
        value = getattr(quote, field)
        assert str(value).startswith(str(expected_value))
