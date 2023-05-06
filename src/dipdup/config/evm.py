from typing import Literal

from pydantic import validator
from pydantic.dataclasses import dataclass

from dipdup.config import ContractConfig
from dipdup.exceptions import ConfigurationError

EVM_ADDRESS_PREFIXES = ('0x',)
EVM_ADDRESS_LENGTH = 42


@dataclass
class EvmContractConfig(ContractConfig):
    """Contract config

    :param address: Contract address
    :param typename: User-defined alias for the contract script
    """

    kind: Literal['evm']
    address: str | None = None
    abi: str | None = None
    typename: str | None = None

    @validator('address', allow_reuse=True)
    def _valid_address(cls, v: str | None) -> str | None:
        # NOTE: Environment substitution was disabled during export, skip validation
        if not v or '$' in v:
            return v

        # TODO: Use eth_utils to validate address + normalize (convert to non-checksum form)
        # https://coincodex.com/article/2078/ethereum-address-checksum-explained/

        if not v.startswith(EVM_ADDRESS_PREFIXES) or len(v) != EVM_ADDRESS_LENGTH:
            raise ValueError(f'`{v}` is not a valid Ethereum address')

        return v

    def get_address(self) -> str:
        if self.address is None:
            raise ConfigurationError(f'`contracts.{self.name}`: `address` field is required`')
        return self.address
