from typing import NotRequired

from typing_extensions import TypedDict

from dipdup.models._subsquid import AbstractSubsquidQuery


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
        'accessList': bool,
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
    callSighash: bool
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
    revertReason: bool
    rewardAuthor: bool
    rewardType: bool
    rewardValue: bool
    subtraces: bool
    suicideAddress: bool
    suicideBalance: bool
    suicideRefundAddress: bool
    traceAddress: bool
    transactionIndex: bool


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
    address: list[str]
    topic0: list[str]
    topic1: list[str]
    topic2: list[str]
    topic3: list[str]
    transaction: bool
    transactionLogs: bool
    transactionTraces: bool


TransactionRequest = TypedDict(
    'TransactionRequest',
    {
        'firstNonce': int,
        'from': list[str],
        'lastNonce': int,
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
    createResultAddress: list[str]
    parents: bool
    rewardAuthor: list[str]
    subtraces: bool
    suicideRefundAddress: list[str]
    transaction: bool
    transactionLogs: bool
    type: list[str]


class StateDiffRequest(TypedDict, total=False):
    address: list[str]
    key: list[str]
    kind: list[str]
    transaction: bool


class Query(AbstractSubsquidQuery):
    logs: NotRequired[list[LogRequest]]
    stateDiffs: NotRequired[list[StateDiffRequest]]
    traces: NotRequired[list[TraceRequest]]
    transactions: NotRequired[list[TransactionRequest]]
    type: NotRequired[str]
    fields: NotRequired[FieldSelection]
