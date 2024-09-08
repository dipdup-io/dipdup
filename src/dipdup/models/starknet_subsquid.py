from typing import NotRequired
from typing import TypedDict

from dipdup.models._subsquid import AbstractSubsquidQuery


class BlockFieldSelection(TypedDict, total=False):
    parentHash: bool
    status: bool
    newRoot: bool
    timestamp: bool
    sequencerAddress: bool


class TransactionFieldSelection(TypedDict, total=False):
    transactionHash: bool
    contractAddress: bool
    entryPointSelector: bool
    calldata: bool
    maxFee: bool
    type: bool
    senderAddress: bool
    version: bool
    signature: bool
    nonce: bool
    classHash: bool
    compiledClassHash: bool
    contractAddressSalt: bool
    constructorCalldata: bool


class EventFieldSelection(TypedDict, total=False):
    fromAddress: bool
    keys: bool
    data: bool


class FieldSelection(TypedDict, total=False):
    block: BlockFieldSelection
    transaction: TransactionFieldSelection
    event: EventFieldSelection


class TransactionRequest(TypedDict, total=False):
    contractAddress: list[str]
    senderAddress: list[str]
    type: list[str]
    firstNonce: int
    lastNonce: int
    events: bool


class EventRequest(TypedDict, total=False):
    fromAddress: list[str]
    key0: list[str]
    key1: list[str]
    key2: list[str]
    key3: list[str]
    transaction: bool


class Query(AbstractSubsquidQuery):
    # NOTE: should always be starknet
    type: NotRequired[str]

    transactions: NotRequired[list[TransactionRequest]]
    events: NotRequired[list[EventRequest]]
    fields: NotRequired[FieldSelection]
