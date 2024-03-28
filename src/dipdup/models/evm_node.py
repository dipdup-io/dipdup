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
class EvmNodeLogData(HasLevel):
    address: str
    block_hash: str
    data: str
    level: int
    log_index: int
    topics: tuple[str, ...]
    transaction_hash: str
    transaction_index: int
    removed: bool

    timestamp: int

    @classmethod
    def from_json(cls, log_json: dict[str, Any], timestamp: int) -> 'EvmNodeLogData':
        # NOTE: Skale Nebula
        if 'removed' not in log_json:
            log_json['removed'] = False

        return cls(
            address=log_json['address'],
            block_hash=log_json['blockHash'],
            data=log_json['data'],
            level=int(log_json['blockNumber'], 16),
            log_index=int(log_json['logIndex'], 16),
            topics=log_json['topics'],
            transaction_hash=log_json['transactionHash'],
            transaction_index=int(log_json['transactionIndex'], 16),
            removed=log_json['removed'],
            timestamp=timestamp,
        )


@dataclass(frozen=True)
class EvmNodeTraceData(HasLevel): ...


@dataclass(frozen=True)
class EvmNodeTransactionData(HasLevel):
    access_list: tuple[dict[str, Any], ...] | None
    block_hash: str
    chain_id: int | None
    data: str | None
    from_: str
    gas: int
    gas_price: int
    hash: str
    input: str
    level: int
    max_fee_per_gas: int | None
    max_priority_fee_per_gas: int | None
    nonce: int
    r: str | None
    s: str | None
    timestamp: int
    to: str | None
    transaction_index: int | None
    type: int | None
    value: int | None
    v: int | None

    @property
    def sighash(self) -> str:
        return self.input[:10]

    @classmethod
    def from_json(cls, transaction_json: dict[str, Any], timestamp: int) -> 'EvmNodeTransactionData':
        return cls(
            access_list=tuple(transaction_json['accessList']) if 'accessList' in transaction_json else None,
            block_hash=transaction_json['blockHash'],
            chain_id=int(transaction_json['chainId'], 16) if 'chainId' in transaction_json else None,
            data=transaction_json.get('data'),
            from_=transaction_json['from'],
            gas=int(transaction_json['gas'], 16),
            gas_price=int(transaction_json['gasPrice'], 16),
            hash=transaction_json['hash'],
            input=transaction_json['input'],
            level=int(transaction_json['blockNumber'], 16),
            max_fee_per_gas=int(transaction_json['maxFeePerGas'], 16) if 'maxFeePerGas' in transaction_json else None,
            max_priority_fee_per_gas=(
                int(transaction_json['maxPriorityFeePerGas'], 16)
                if 'maxPriorityFeePerGas' in transaction_json
                else None
            ),
            nonce=int(transaction_json['nonce'], 16),
            r=transaction_json.get('r'),
            s=transaction_json.get('s'),
            timestamp=timestamp,
            to=transaction_json.get('to'),
            transaction_index=(
                int(transaction_json['transactionIndex'], 16) if 'transactionIndex' in transaction_json else None
            ),
            type=int(transaction_json['type'], 16) if 'type' in transaction_json else None,
            value=int(transaction_json['value'], 16) if 'value' in transaction_json else None,
            v=int(transaction_json['v'], 16) if 'v' in transaction_json else None,
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
