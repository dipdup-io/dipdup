from enum import Enum
from typing import Any
from typing import Generic
from typing import NotRequired
from typing import TypedDict
from typing import TypeVar

from pydantic import BaseModel
from pydantic.dataclasses import dataclass

from dipdup.fetcher import HasLevel
from dipdup.models.evm_node import EvmNodeLogData

PayloadT = TypeVar('PayloadT', bound=BaseModel)


class BlockFieldSelection(TypedDict, total=False):
    number: bool
    hash: bool
    parentHash: bool
    timestamp: bool
    transactionsRoot: bool
    receiptsRoot: bool
    stateRoot: bool
    logsBloom: bool
    sha3Uncles: bool
    extraData: bool
    miner: bool
    nonce: bool
    mixHash: bool
    size: bool
    gasLimit: bool
    gasUsed: bool
    difficulty: bool
    totalDifficulty: bool
    baseFeePerGas: bool


TransactionFieldSelection = TypedDict(
    'TransactionFieldSelection',
    {
        'transactionIndex': bool,
        'hash': bool,
        'nonce': bool,
        'from': bool,
        'to': bool,
        'input': bool,
        'value': bool,
        'gas': bool,
        'gasPrice': bool,
        'maxFeePerGas': bool,
        'maxPriorityFeePerGas': bool,
        'v': bool,
        'r': bool,
        's': bool,
        'yParity': bool,
        'chainId': bool,
        'sighash': bool,
        'gasUsed': bool,
        'cumulativeGasUsed': bool,
        'effectiveGasUsed': bool,
        'type': bool,
        'status': bool,
    },
    total=False,
)


class LogFieldSelection(TypedDict, total=False):
    logIndex: bool
    transactionIndex: bool
    transactionHash: bool
    address: bool
    data: bool
    topics: bool


class TraceFieldSelection(TypedDict, total=False):
    traceAddress: bool
    subtraces: bool
    transactionIndex: bool
    type: bool
    error: bool
    createFrom: bool
    createValue: bool
    createGas: bool
    createInit: bool
    createResultGasUsed: bool
    createResultCode: bool
    createResultAddress: bool
    callFrom: bool
    callTo: bool
    callValue: bool
    callGas: bool
    callInput: bool
    callType: bool
    callResultGasUsed: bool
    callResultOutput: bool
    suicideAddress: bool
    suicideRefundAddress: bool
    suicideBalance: bool
    rewardAuthor: bool
    rewardValue: bool
    rewardType: bool


class StateDiffFieldSelection(TypedDict, total=False):
    transactionIndex: bool
    address: bool
    key: bool
    kind: bool
    prev: bool
    next: bool


class FieldSelection(TypedDict, total=False):
    block: BlockFieldSelection
    transaction: TransactionFieldSelection
    log: LogFieldSelection
    trace: TraceFieldSelection
    stateDiff: StateDiffFieldSelection


class LogRequest(TypedDict, total=False):
    address: NotRequired[list[str]]
    topic0: NotRequired[list[str]]
    transaction: bool


TransactionRequest = TypedDict(
    'TransactionRequest',
    {
        'from': list[str],
        'to': list[str],
        'sighash': list[str],
        'logs': bool,
        'traces': bool,
        'stateDiffs': bool,
    },
    total=False,
)


class TraceRequest(TypedDict, total=False):
    type: list[str]
    createFrom: list[str]
    callFrom: list[str]
    callTo: list[str]
    callSighash: list[str]
    suicideRefundAddress: list[str]
    rewardAuthor: list[str]
    transaction: bool
    subtraces: bool


class StateDiffRequest(TypedDict, total=False):
    address: list[str]
    key: list[str]
    kind: list[str]
    transaction: bool


class Query(TypedDict):
    fromBlock: int
    toBlock: NotRequired[int]
    includeAllBlocks: NotRequired[bool]
    fields: NotRequired[FieldSelection]
    logs: NotRequired[list[LogRequest]]
    transactions: NotRequired[list[TransactionRequest]]
    traces: NotRequired[list[TraceRequest]]
    stateDiffs: NotRequired[list[StateDiffRequest]]


class SubsquidMessageType(Enum):
    blocks = 'blocks'
    logs = 'logs'
    traces = 'traces'
    transactions = 'transactions'


@dataclass(frozen=True)
class SubsquidEventData(HasLevel):
    address: str
    data: str
    log_index: int
    topics: tuple[str, ...]
    transaction_hash: str
    transaction_index: int
    block_number: int
    timestamp: int

    @classmethod
    def from_json(
        cls,
        event_json: dict[str, Any],
        level: int,
        timestamp: int,
    ) -> 'SubsquidEventData':
        return SubsquidEventData(
            address=event_json['address'],
            data=event_json['data'],
            topics=tuple(event_json['topics']),
            log_index=event_json['logIndex'],
            transaction_hash=event_json['transactionHash'],
            transaction_index=event_json['transactionIndex'],
            block_number=level,
            timestamp=timestamp,
        )

    @property
    def level(self) -> int:  # type: ignore[override]
        return self.block_number


@dataclass(frozen=True)
class SubsquidTraceData(HasLevel): ...


@dataclass(frozen=True)
class SubsquidTransactionData(HasLevel):
    transaction_index: int
    hash: str
    nonce: int
    from_: str
    to: str
    input: str
    value: int
    gas: int
    gas_price: int
    max_fee_per_gas: int
    max_priority_fee_per_gas: int
    v: int
    r: str
    s: str
    y_parity: bool
    chain_id: int
    sighash: str
    gas_used: int
    cumulative_gas_used: int
    effective_gas_used: int
    type: int
    status: int
    level: int

    @classmethod
    def from_json(
        cls,
        transaction_json: dict[str, Any],
        level: int,
    ) -> 'SubsquidTransactionData':
        return SubsquidTransactionData(
            transaction_index=transaction_json['transactionIndex'],
            hash=transaction_json['hash'],
            nonce=transaction_json['nonce'],
            from_=transaction_json['from'],
            to=transaction_json['to'],
            input=transaction_json['input'],
            value=transaction_json['value'],
            gas=transaction_json['gas'],
            gas_price=transaction_json['gasPrice'],
            max_fee_per_gas=transaction_json['maxFeePerGas'],
            max_priority_fee_per_gas=transaction_json['maxPriorityFeePerGas'],
            v=transaction_json['v'],
            r=transaction_json['r'],
            s=transaction_json['s'],
            y_parity=transaction_json['yParity'],
            chain_id=transaction_json['chainId'],
            sighash=transaction_json['sighash'],
            gas_used=transaction_json['gasUsed'],
            cumulative_gas_used=transaction_json['cumulativeGasUsed'],
            effective_gas_used=transaction_json['effectiveGasUsed'],
            type=transaction_json['type'],
            status=transaction_json['status'],
            level=level,
        )


@dataclass(frozen=True)
class SubsquidEvent(Generic[PayloadT]):
    data: SubsquidEventData | EvmNodeLogData
    payload: PayloadT


@dataclass(frozen=True)
class SubsquidTrace(Generic[PayloadT]): ...


@dataclass(frozen=True)
class SubsquidTransaction(Generic[PayloadT]): ...
