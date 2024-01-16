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
from dipdup.models.evm_node import EvmNodeTransactionData

PayloadT = TypeVar('PayloadT', bound=BaseModel)
InputT = TypeVar('InputT', bound=BaseModel)


class BlockFieldSelection(TypedDict, total=False):
    baseFeePerGas: bool
    difficulty: bool
    extraData: bool
    gasLimit: bool
    gasUsed: bool
    hash: bool
    logsBloom: bool
    miner: bool
    mixHash: bool
    nonce: bool
    number: bool
    parentHash: bool
    receiptsRoot: bool
    sha3Uncles: bool
    size: bool
    stateRoot: bool
    timestamp: bool
    totalDifficulty: bool
    transactionsRoot: bool


TransactionFieldSelection = TypedDict(
    'TransactionFieldSelection',
    {
        'chainId': bool,
        'contractAddress': bool,
        'cumulativeGasUsed': bool,
        'effectiveGasPrice': bool,
        'from': bool,
        'gas': bool,
        'gasPrice': bool,
        'gasUsed': bool,
        'hash': bool,
        'input': bool,
        'maxFeePerGas': bool,
        'maxPriorityFeePerGas': bool,
        'nonce': bool,
        'r': bool,
        's': bool,
        'sighash': bool,
        'status': bool,
        'to': bool,
        'transactionIndex': bool,
        'type': bool,
        'value': bool,
        'v': bool,
        'yParity': bool,
    },
    total=False,
)


class LogFieldSelection(TypedDict, total=False):
    address: bool
    data: bool
    logIndex: bool
    topics: bool
    transactionHash: bool
    transactionIndex: bool


class TraceFieldSelection(TypedDict, total=False):
    callFrom: bool
    callGas: bool
    callInput: bool
    callResultGasUsed: bool
    callResultOutput: bool
    callTo: bool
    callType: bool
    callValue: bool
    createFrom: bool
    createGas: bool
    createInit: bool
    createResultAddress: bool
    createResultCode: bool
    createResultGasUsed: bool
    createValue: bool
    error: bool
    rewardAuthor: bool
    rewardType: bool
    rewardValue: bool
    subtraces: bool
    suicideAddress: bool
    suicideBalance: bool
    suicideRefundAddress: bool
    traceAddress: bool
    transactionIndex: bool
    type: bool


class StateDiffFieldSelection(TypedDict, total=False):
    address: bool
    key: bool
    kind: bool
    next: bool
    prev: bool
    transactionIndex: bool


class FieldSelection(TypedDict, total=False):
    block: BlockFieldSelection
    log: LogFieldSelection
    stateDiff: StateDiffFieldSelection
    trace: TraceFieldSelection
    transaction: TransactionFieldSelection


class LogRequest(TypedDict, total=False):
    address: NotRequired[list[str]]
    topic0: NotRequired[list[str]]
    transaction: bool


TransactionRequest = TypedDict(
    'TransactionRequest',
    {
        'from': list[str],
        'logs': bool,
        'sighash': list[str],
        'stateDiffs': bool,
        'to': list[str],
        'traces': bool,
    },
    total=False,
)


class TraceRequest(TypedDict, total=False):
    callFrom: list[str]
    callSighash: list[str]
    callTo: list[str]
    createFrom: list[str]
    rewardAuthor: list[str]
    subtraces: bool
    suicideRefundAddress: list[str]
    transaction: bool
    type: list[str]


class StateDiffRequest(TypedDict, total=False):
    address: list[str]
    key: list[str]
    kind: list[str]
    transaction: bool


class Query(TypedDict):
    fields: NotRequired[FieldSelection]
    fromBlock: int
    includeAllBlocks: NotRequired[bool]
    logs: NotRequired[list[LogRequest]]
    stateDiffs: NotRequired[list[StateDiffRequest]]
    toBlock: NotRequired[int]
    traces: NotRequired[list[TraceRequest]]
    transactions: NotRequired[list[TransactionRequest]]


class SubsquidMessageType(Enum):
    blocks = 'blocks'
    logs = 'logs'
    traces = 'traces'
    transactions = 'transactions'


@dataclass(frozen=True)
class SubsquidEventData(HasLevel):
    address: str
    data: str
    level: int
    log_index: int
    timestamp: int
    topics: tuple[str, ...]
    transaction_hash: str
    transaction_index: int

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
            level=level,
            log_index=event_json['logIndex'],
            timestamp=timestamp,
            topics=tuple(event_json['topics']),
            transaction_hash=event_json['transactionHash'],
            transaction_index=event_json['transactionIndex'],
        )


@dataclass(frozen=True)
class SubsquidTraceData(HasLevel): ...


@dataclass(frozen=True)
class SubsquidTransactionData(HasLevel):
    chain_id: int | None
    cumulative_gas_used: int | None
    contract_address: str | None
    effective_gas_price: int | None
    from_: str
    gas: int
    gas_price: int
    gas_used: int
    hash: str
    input: str
    level: int
    max_fee_per_gas: int | None
    max_priority_fee_per_gas: int | None
    nonce: int
    r: str | None
    s: str | None
    sighash: str
    status: int | None
    timestamp: int
    to: str
    transaction_index: int
    type: int | None
    value: int
    v: int | None
    y_parity: bool | None

    @classmethod
    def from_json(
        cls,
        transaction_json: dict[str, Any],
        level: int,
        timestamp: int,
    ) -> 'SubsquidTransactionData':
        cumulative_gas_used = (
            int(transaction_json['cumulativeGasUsed'], 16) if transaction_json['cumulativeGasUsed'] else None
        )
        effective_gas_price = (
            int(transaction_json['effectiveGasPrice'], 16) if transaction_json['effectiveGasPrice'] else None
        )
        max_fee_per_gas = int(transaction_json['maxFeePerGas'], 16) if transaction_json['maxFeePerGas'] else None
        max_priority_fee_per_gas = (
            int(transaction_json['maxPriorityFeePerGas'], 16) if transaction_json['maxPriorityFeePerGas'] else None
        )
        v = int(transaction_json['v'], 16) if transaction_json['v'] else None
        y_parity = bool(int(transaction_json['yParity'], 16)) if transaction_json['yParity'] else None
        return SubsquidTransactionData(
            chain_id=transaction_json['chainId'],
            cumulative_gas_used=cumulative_gas_used,
            contract_address=transaction_json['contractAddress'],
            effective_gas_price=effective_gas_price,
            from_=transaction_json['from'],
            gas=int(transaction_json['gas'], 16),
            gas_price=int(transaction_json['gasPrice'], 16),
            gas_used=int(transaction_json['gasUsed'], 16),
            hash=transaction_json['hash'],
            input=transaction_json['input'],
            level=level,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            nonce=transaction_json['nonce'],
            r=transaction_json['r'],
            s=transaction_json['s'],
            sighash=transaction_json['sighash'],
            status=transaction_json['status'],
            timestamp=timestamp,
            to=transaction_json['to'],
            transaction_index=transaction_json['transactionIndex'],
            type=transaction_json['type'],
            value=int(transaction_json['value'], 16),
            v=v,
            y_parity=y_parity,
        )


@dataclass(frozen=True)
class SubsquidEvent(Generic[PayloadT]):
    data: SubsquidEventData | EvmNodeLogData
    payload: PayloadT


@dataclass(frozen=True)
class SubsquidTrace(Generic[PayloadT]): ...


@dataclass(frozen=True)
class SubsquidTransaction(Generic[InputT]):
    data: SubsquidTransactionData | EvmNodeTransactionData
    input: InputT
