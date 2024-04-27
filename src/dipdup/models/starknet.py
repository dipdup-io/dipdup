from abc import ABC
from dataclasses import dataclass
from typing import Any
from typing import Self

from dipdup.fetcher import HasLevel


@dataclass(frozen=True)
class StarknetTransactionData(HasLevel, ABC):
    level: int
    block_hash: str
    transaction_index: int
    transaction_hash: str
    timestamp: int

    contract_address: str | None  # Address of the contract for contract-related transactions
    entry_point_selector: str | None
    calldata: tuple[str, ...] | None
    max_fee: str | None
    version: str
    signature: tuple[str, ...] | None
    nonce: str | None
    type: str  # transaction type enum
    sender_address: str | None
    class_hash: str | None
    compiled_class_hash: str | None
    contract_address_salt: str | None
    constructor_calldata: tuple[str, ...] | None

    @classmethod
    def from_subsquid_json(cls, transaction_json: dict[str, Any], header: dict[str, Any]) -> Self:
        return cls(
            level=header['number'],
            block_hash=header['hash'],
            transaction_index=transaction_json['transactionIndex'],
            transaction_hash=transaction_json['transactionHash'],
            timestamp=header['timestamp'],
            contract_address=transaction_json['contractAddress'],
            entry_point_selector=transaction_json.get('entryPointSelector'),
            calldata=tuple(transaction_json.get('calldata', []) or []),
            max_fee=transaction_json.get('maxFee'),
            version=transaction_json['version'],
            signature=tuple(transaction_json.get('signature', []) or []),
            nonce=transaction_json.get('nonce'),
            type=transaction_json['type'],
            sender_address=transaction_json.get('senderAddress'),
            class_hash=transaction_json.get('classHash'),
            compiled_class_hash=transaction_json.get('compiledClassHash'),
            contract_address_salt=transaction_json.get('contractAddressSalt'),
            constructor_calldata=tuple(transaction_json.get('constructorCalldata', []) or []),
        )


@dataclass(frozen=True)
class StarknetEventData(HasLevel, ABC):
    level: int
    block_hash: str
    transaction_index: int
    # TODO: transaction hash
    timestamp: int

    from_address: str
    keys: tuple[str, ...]
    data: tuple[str, ...]

    @classmethod
    def from_subsquid_json(cls, event_json: dict[str, Any], header: dict[str, Any]) -> Self:
        return cls(
            level=header['number'],
            block_hash=header['hash'],
            transaction_index=event_json['transactionIndex'],
            timestamp=header['timestamp'],
            from_address=event_json['fromAddress'],
            keys=tuple(event_json['keys']),
            data=tuple(event_json['data']),
        )
