from abc import ABC
from dataclasses import dataclass
from typing import Any
from typing import Self

from dipdup.fetcher import HasLevel


@dataclass(frozen=True)
class StarknetTransactionData(HasLevel, ABC):
    transaction_index: int
    transaction_hash: str

    contract_address: str | None  # Address of the contract for contract-related transactions
    entry_point_selector: str | None
    calldata: list[str] | None
    max_fee: str | None
    version: str
    signature: list[str] | None
    nonce: str | None
    type: str  # transaction type enum
    sender_address: str | None
    class_hash: str | None
    compiled_class_hash: str | None
    contract_address_salt: str | None
    constructor_calldata: list[str] | None
    block_number: int

    @classmethod
    def from_subsquid_json(
        cls,
        transaction_json: dict[str, Any],
    ) -> Self:
        return cls(**transaction_json)
