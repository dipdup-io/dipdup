from abc import ABC
from typing import Any
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.subscriptions import Subscription


class EvmNodeSubscription(ABC, Subscription):
    name: str

    def get_params(self) -> list[Any]:
        return [self.name]


@dataclass(frozen=True)
class EvmNodeNewHeadsSubscription(EvmNodeSubscription):
    name: Literal['newHeads'] = 'newHeads'


@dataclass(frozen=True)
class EvmNodeLogsSubscription(EvmNodeSubscription):
    name: Literal['logs'] = 'logs'
    address: str | tuple[str, ...] | None = None
    topics: tuple[tuple[str, ...], ...] | None = None

    def get_params(self) -> list[Any]:
        return super().get_params() + [
            {
                'address': self.address,
                'topics': self.topics,
            }
        ]


@dataclass(frozen=True)
class EvmNodeSyncingSubscription(EvmNodeSubscription):
    name: Literal['syncing'] = 'syncing'


# FIXME: Frozen?
@dataclass
class EvmNodeHeadData:
    number: str
    hash: str
    parent_hash: str
    sha3_uncles: str
    logs_bloom: str
    transactions_root: str
    state_root: str
    receipts_root: str
    miner: str
    difficulty: str
    extra_data: str
    gas_limit: str
    gas_used: str
    timestamp: str
    base_fee_per_gas: str
    withdrawals_root: str
    nonce: str
    mix_hash: str

    @classmethod
    def from_json(cls, block_json: dict[str, Any]) -> 'EvmNodeHeadData':
        return cls(
            number=block_json['number'],
            hash=block_json['hash'],
            parent_hash=block_json['parentHash'],
            sha3_uncles=block_json['sha3Uncles'],
            logs_bloom=block_json['logsBloom'],
            transactions_root=block_json['transactionsRoot'],
            state_root=block_json['stateRoot'],
            receipts_root=block_json['receiptsRoot'],
            miner=block_json['miner'],
            difficulty=block_json['difficulty'],
            extra_data=block_json['extraData'],
            gas_limit=block_json['gasLimit'],
            gas_used=block_json['gasUsed'],
            timestamp=block_json['timestamp'],
            base_fee_per_gas=block_json['baseFeePerGas'],
            withdrawals_root=block_json['withdrawalsRoot'],
            nonce=block_json['nonce'],
            mix_hash=block_json['mixHash'],
        )


@dataclass
class EvmNodeLogData:
    address: str
    topics: list[str]
    data: str
    block_number: str
    transaction_hash: str
    transaction_index: str
    log_index: str
    removed: bool

    @classmethod
    def from_json(cls, log_json: dict[str, Any]) -> 'EvmNodeLogData':
        return cls(
            address=log_json['address'],
            topics=log_json['topics'],
            data=log_json['data'],
            block_number=log_json['blockNumber'],
            transaction_hash=log_json['transactionHash'],
            transaction_index=log_json['transactionIndex'],
            log_index=log_json['logIndex'],
            removed=log_json['removed'],
        )

    @property
    def level(self) -> int:
        return int(self.block_number, 16)

    @property
    def index(self) -> str:
        return self.log_index


@dataclass
class EvmNodeSyncingData:
    starting_block: str
    current_block: str
    highest_block: str

    @classmethod
    def from_json(cls, syncing_json: dict[str, Any]) -> 'EvmNodeSyncingData':
        return cls(
            starting_block=syncing_json['startingBlock'],
            current_block=syncing_json['currentBlock'],
            highest_block=syncing_json['highestBlock'],
        )
