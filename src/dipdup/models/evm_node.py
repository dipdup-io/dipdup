from abc import ABC
from typing import Any
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.fetcher import HasLevel
from dipdup.subscriptions import Subscription


class EvmNodeSubscription(ABC, Subscription):
    name: str

    def get_params(self) -> list[Any]:
        return [self.name]


@dataclass(frozen=True)
class EvmNodeHeadSubscription(EvmNodeSubscription):
    name: Literal['newHeads'] = 'newHeads'
    transactions: bool = False


@dataclass(frozen=True)
class EvmNodeLogsSubscription(EvmNodeSubscription):
    name: Literal['logs'] = 'logs'
    address: str | tuple[str, ...] | None = None
    topics: tuple[tuple[str, ...], ...] | None = None

    def get_params(self) -> list[Any]:
        return [
            *super().get_params(),
            {'address': self.address, 'topics': self.topics},
        ]


@dataclass(frozen=True)
class EvmNodeSyncingSubscription(EvmNodeSubscription):
    name: Literal['syncing'] = 'syncing'


@dataclass(frozen=True)
class EvmNodeHeadData(HasLevel):
    base_fee_per_gas: int
    difficulty: int
    extra_data: str
    gas_limit: int
    gas_used: int
    hash: str
    level: int
    logs_bloom: str
    miner: str
    mix_hash: str
    nonce: str
    number: int
    parent_hash: str
    receipts_root: str
    sha3_uncles: str
    state_root: str
    timestamp: int
    transactions_root: str
    withdrawals_root: str | None

    @classmethod
    def from_json(cls, block_json: dict[str, Any]) -> 'EvmNodeHeadData':
        # NOTE: Skale Nebula
        if 'baseFeePerGas' not in block_json:
            block_json['baseFeePerGas'] = '0x0'

        return cls(
            base_fee_per_gas=int(block_json['baseFeePerGas'], 16),
            difficulty=int(block_json['difficulty'], 16),
            extra_data=block_json['extraData'],
            gas_limit=int(block_json['gasLimit'], 16),
            gas_used=int(block_json['gasUsed'], 16),
            hash=block_json['hash'],
            level=int(block_json['number'], 16),
            logs_bloom=block_json['logsBloom'],
            miner=block_json['miner'],
            mix_hash=block_json['mixHash'],
            nonce=block_json['nonce'],
            number=int(block_json['number'], 16),
            parent_hash=block_json['parentHash'],
            receipts_root=block_json['receiptsRoot'],
            sha3_uncles=block_json['sha3Uncles'],
            state_root=block_json['stateRoot'],
            timestamp=int(block_json['timestamp'], 16),
            transactions_root=block_json['transactionsRoot'],
            withdrawals_root=block_json.get('withdrawalsRoot', None),
        )


@dataclass(frozen=True)
class EvmNodeSyncingData:
    current_block: int
    highest_block: int
    starting_block: int

    @classmethod
    def from_json(cls, syncing_json: dict[str, Any]) -> 'EvmNodeSyncingData':
        return cls(
            current_block=int(syncing_json['currentBlock'], 16),
            highest_block=int(syncing_json['highestBlock'], 16),
            starting_block=int(syncing_json['startingBlock'], 16),
        )
