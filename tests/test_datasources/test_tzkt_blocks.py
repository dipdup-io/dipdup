import json

import pytest

from dipdup.models.tezos_tzkt import TzktBlockData


@pytest.mark.parametrize(
    'tzkt_block_json',
    [
        '{"cycle":524,"level":2706800,"hash":"BLNtxuniowUUtyx4UtWDZCckQsp9rF89MRk3BZZvMWoXNDSqsLx","timestamp":"2022-09-13T14:10:59Z","proto":13,"payloadRound":0,"blockRound":0,"validations":6969,"deposit":0,"reward":10000000,"bonus":9866372,"fees":213751,"nonceRevealed":false,"proposer":{"address":"tz1Nf6tsK4G6bBqgSQERy4nUtkHNKUVdh7q1"},"producer":{"address":"tz1Nf6tsK4G6bBqgSQERy4nUtkHNKUVdh7q1"},"software":{"version":"v13.0","date":"2022-05-05T12:55:26Z"},"lbToggle":true,"lbToggleEma":376475923,"priority":0,"baker":{"address":"tz1Nf6tsK4G6bBqgSQERy4nUtkHNKUVdh7q1"},"lbEscapeVote":false,"lbEscapeEma":376475923}',
    ],
)
async def test_deprecated_priority(tzkt_block_json: str) -> None:
    tzkt_block_dict = json.loads(tzkt_block_json)
    block = TzktBlockData.from_json(tzkt_block_dict)
    assert block
    assert isinstance(block, TzktBlockData)
    assert block.priority == 0

    del tzkt_block_dict['priority']

    block = TzktBlockData.from_json(tzkt_block_dict)
    assert block
    assert isinstance(block, TzktBlockData)
    assert block.priority is None
