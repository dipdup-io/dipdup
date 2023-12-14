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
class EvmNodeHeadsSubscription(EvmNodeSubscription):
    name: Literal['newHeads'] = 'newHeads'


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
class EvmNodeTransactionsSubscription(EvmNodeSubscription):
    name: Literal['newPendingTransactions'] = 'newPendingTransactions'


@dataclass(frozen=True)
class EvmNodeSyncingSubscription(EvmNodeSubscription):
    name: Literal['syncing'] = 'syncing'


@dataclass(frozen=True)
class EvmNodeHeadData:
    number: int
    hash: str
    parent_hash: str
    sha3_uncles: str
    logs_bloom: str
    transactions_root: str
    state_root: str
    receipts_root: str
    miner: str
    difficulty: int
    extra_data: str
    gas_limit: int
    gas_used: int
    timestamp: int
    base_fee_per_gas: int
    withdrawals_root: str
    nonce: str
    mix_hash: str

    @classmethod
    def from_json(cls, block_json: dict[str, Any]) -> 'EvmNodeHeadData':
        return cls(
            number=int(block_json['number'], 16),
            hash=block_json['hash'],
            parent_hash=block_json['parentHash'],
            sha3_uncles=block_json['sha3Uncles'],
            logs_bloom=block_json['logsBloom'],
            transactions_root=block_json['transactionsRoot'],
            state_root=block_json['stateRoot'],
            receipts_root=block_json['receiptsRoot'],
            miner=block_json['miner'],
            difficulty=int(block_json['difficulty'], 16),
            extra_data=block_json['extraData'],
            gas_limit=int(block_json['gasLimit'], 16),
            gas_used=int(block_json['gasUsed'], 16),
            timestamp=int(block_json['timestamp'], 16),
            base_fee_per_gas=int(block_json['baseFeePerGas'], 16),
            withdrawals_root=block_json['withdrawalsRoot'],
            nonce=block_json['nonce'],
            mix_hash=block_json['mixHash'],
        )

    @property
    def level(self) -> int:
        return self.number


@dataclass(frozen=True)
class EvmNodeLogData:
    address: str
    block_hash: str
    block_number: int
    data: str
    log_index: int
    topics: tuple[str, ...]
    transaction_hash: str
    transaction_index: int
    removed: bool

    timestamp: int

    @classmethod
    def from_json(cls, log_json: dict[str, Any], timestamp: int) -> 'EvmNodeLogData':
        return cls(
            address=log_json['address'],
            block_hash=log_json['blockHash'],
            block_number=int(log_json['blockNumber'], 16),
            data=log_json['data'],
            log_index=int(log_json['logIndex'], 16),
            topics=log_json['topics'],
            transaction_hash=log_json['transactionHash'],
            transaction_index=int(log_json['transactionIndex'], 16),
            removed=log_json['removed'],
            timestamp=timestamp,
        )

    @property
    def level(self) -> int:
        return self.block_number


@dataclass(frozen=True)
class EvmNodeTraceData: ...


@dataclass(frozen=True)
class EvmNodeTransactionData:
    access_list: tuple[dict[str, Any], ...]
    block_hash: str
    block_number: int
    chain_id: int
    data: str
    from_: str
    gas: int
    gas_price: int
    max_fee_per_gas: int
    max_priority_fee_per_gas: int
    hash: str
    input: str
    nonce: int
    r: str
    s: str
    to: str
    transaction_index: int
    type: int
    v: int
    value: int

    @classmethod
    def from_json(cls, transaction_json: dict[str, Any]) -> 'EvmNodeTransactionData':
        return cls(
            access_list=tuple(transaction_json['accessList']),
            block_hash=transaction_json['blockHash'],
            block_number=int(transaction_json['blockNumber'], 16),
            chain_id=int(transaction_json['chainId'], 16),
            data=transaction_json['data'],
            from_=transaction_json['from'],
            gas=int(transaction_json['gas'], 16),
            gas_price=int(transaction_json['gasPrice'], 16),
            max_fee_per_gas=int(transaction_json['maxFeePerGas'], 16),
            max_priority_fee_per_gas=int(transaction_json['maxPriorityFeePerGas'], 16),
            hash=transaction_json['hash'],
            input=transaction_json['input'],
            nonce=int(transaction_json['nonce'], 16),
            r=transaction_json['r'],
            s=transaction_json['s'],
            to=transaction_json['to'],
            transaction_index=int(transaction_json['transactionIndex'], 16),
            type=transaction_json['type'],
            v=int(transaction_json['v'], 16),
            value=int(transaction_json['value'], 16),
        )

    @property
    def level(self) -> int:
        return self.block_number


@dataclass(frozen=True)
class EvmNodeSyncingData:
    starting_block: int
    current_block: int
    highest_block: int

    @classmethod
    def from_json(cls, syncing_json: dict[str, Any]) -> 'EvmNodeSyncingData':
        return cls(
            starting_block=int(syncing_json['startingBlock'], 16),
            current_block=int(syncing_json['currentBlock'], 16),
            highest_block=int(syncing_json['highestBlock'], 16),
        )
