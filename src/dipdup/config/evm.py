from typing import Literal

from pydantic import validator
from pydantic.dataclasses import dataclass

from dipdup.config import ContractConfig

EVM_ADDRESS_PREFIXES = ('0x',)
EVM_ADDRESS_LENGTH = 42


@dataclass
class EvmContractConfig(ContractConfig):
    """Contract config

    :param address: Contract address
    :param code_hash: Contract code hash or address to fetch it from
    :param typename: User-defined alias for the contract script
    """

    kind: Literal['evm']
    address: str

    @validator('address', allow_reuse=True)
    def _valid_address(cls, v: str | None) -> str | None:
        # NOTE: Environment substitution was disabled during export, skip validation
        if not v or '$' in v:
            return v

        if not v.startswith(EVM_ADDRESS_PREFIXES) or len(v) != EVM_ADDRESS_LENGTH:
            raise ValueError(f'`{v}` is not a valid Ethereum address')

        return v
