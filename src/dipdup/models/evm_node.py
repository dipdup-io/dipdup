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
    base_fee_per_gas: int
    difficulty: int
    extra_data: str
    gas_limit: int
    gas_used: int
    hash: str
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
    withdrawals_root: str

    @classmethod
    def from_json(cls, block_json: dict[str, Any]) -> 'EvmNodeHeadData':
        return cls(
            base_fee_per_gas=int(block_json['baseFeePerGas'], 16),
            difficulty=int(block_json['difficulty'], 16),
            extra_data=block_json['extraData'],
            gas_limit=int(block_json['gasLimit'], 16),
            gas_used=int(block_json['gasUsed'], 16),
            hash=block_json['hash'],
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
            withdrawals_root=block_json['withdrawalsRoot'],
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
    hash: str
    input: str
    max_fee_per_gas: int
    max_priority_fee_per_gas: int
    nonce: int
    r: str
    s: str
    to: str
    transaction_index: int
    type: int
    value: int
    v: int

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
            hash=transaction_json['hash'],
            input=transaction_json['input'],
            max_fee_per_gas=int(transaction_json['maxFeePerGas'], 16),
            max_priority_fee_per_gas=int(transaction_json['maxPriorityFeePerGas'], 16),
            nonce=int(transaction_json['nonce'], 16),
            r=transaction_json['r'],
            s=transaction_json['s'],
            to=transaction_json['to'],
            transaction_index=int(transaction_json['transactionIndex'], 16),
            type=transaction_json['type'],
            value=int(transaction_json['value'], 16),
            v=int(transaction_json['v'], 16),
        )

    @property
    def level(self) -> int:
        return self.block_number


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
