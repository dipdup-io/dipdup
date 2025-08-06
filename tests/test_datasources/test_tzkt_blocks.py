import orjson
import pytest

from dipdup.models.tezos import TezosBlockData


@pytest.mark.parametrize(
    'tzkt_block_json',
    [
        '{"cycle":524,"level":2706800,"hash":"BLNtxuniowUUtyx4UtWDZCckQsp9rF89MRk3BZZvMWoXNDSqsLx","timestamp":"2022-09-13T14:10:59Z","proto":13,"payloadRound":0,"blockRound":0,"validations":6969,"deposit":0,"reward":10000000,"bonus":9866372,"fees":213751,"nonceRevealed":false,"proposer":{"address":"tz1Nf6tsK4G6bBqgSQERy4nUtkHNKUVdh7q1"},"producer":{"address":"tz1Nf6tsK4G6bBqgSQERy4nUtkHNKUVdh7q1"},"software":{"version":"v13.0","date":"2022-05-05T12:55:26Z"},"lbToggle":true,"lbToggleEma":376475923,"priority":0,"baker":{"address":"tz1Nf6tsK4G6bBqgSQERy4nUtkHNKUVdh7q1"},"lbEscapeVote":false,"lbEscapeEma":376475923}',
    ],
)
async def test_deprecated_priority(tzkt_block_json: str) -> None:
    tzkt_block_dict = orjson.loads(tzkt_block_json)
    block = TezosBlockData.from_json(tzkt_block_dict)
    assert block
    assert isinstance(block, TezosBlockData)
    assert block.priority == 0

    del tzkt_block_dict['priority']

    block = TezosBlockData.from_json(tzkt_block_dict)
    assert block
    assert isinstance(block, TezosBlockData)
    assert block.priority is None


async def test_seoulnet_response() -> None:
    from dipdup.models.tezos import TezosBlockData
    from dipdup.models.tezos import TezosHeadBlockData

    tzkt_head_json = {
        'chain': 'ghostnet',
        'chainId': 'NetXnHfVqm9iesp',
        'cycle': 1674,
        'level': 14197527,
        'hash': 'BKqV7LnQfrfngY2JqA6Rn4pgXPho5BZPpuJcNLYHNfaLsyeFLoC',
        'protocol': 'PsRiotumaAMotcRoDWW1bysEhQy2n1M5fy8JgRp8jjRfHGmfeA7',
        'nextProtocol': 'PsRiotumaAMotcRoDWW1bysEhQy2n1M5fy8JgRp8jjRfHGmfeA7',
        'timestamp': '2025-08-06T15:38:00Z',
        'votingEpoch': 1326,
        'votingPeriod': 1329,
        'knownLevel': 14197527,
        'lastSync': '2025-08-06T15:38:01Z',
        'synced': True,
        'quoteLevel': 14197527,
        'quoteBtc': 6.76257481962031e-06,
        'quoteEur': 0.6684812122856512,
        'quoteUsd': 0.7780356315250635,
        'quoteCny': 5.588552137681382,
        'quoteJpy': 114.6411710177945,
        'quoteKrw': 1078.1838981305855,
        'quoteEth': 0.00021434607004505848,
        'quoteGbp': 0.5830949138683016,
    }
    tzkt_block_json = {
        'cycle': 1674,
        'level': 14197527,
        'hash': 'BKqV7LnQfrfngY2JqA6Rn4pgXPho5BZPpuJcNLYHNfaLsyeFLoC',
        'timestamp': '2025-08-06T15:38:00Z',
        'proto': 12,
        'payloadRound': 0,
        'blockRound': 0,
        'validations': 6878,
        'deposit': 0,
        'rewardDelegated': 70525,
        'rewardStakedOwn': 48207330,
        'rewardStakedEdge': 0,
        'rewardStakedShared': 0,
        'bonusDelegated': 66787,
        'bonusStakedOwn': 45652271,
        'bonusStakedEdge': 0,
        'bonusStakedShared': 0,
        'fees': 1502,
        'nonceRevealed': False,
        'proposer': {'alias': 'Marco S', 'address': 'tz1Zt8QQ9aBznYNk5LUBjtME9DuExomw9YRs'},
        'producer': {'alias': 'Marco S', 'address': 'tz1Zt8QQ9aBznYNk5LUBjtME9DuExomw9YRs'},
        'software': {'version': 'v22.0', 'date': '2025-04-07T11:33:08Z'},
        'lbToggle': True,
        'lbToggleEma': 1999,
        'aiToggleEma': 1788871656,
    }

    TezosHeadBlockData.from_json(tzkt_head_json)
    TezosBlockData.from_json(tzkt_block_json)
