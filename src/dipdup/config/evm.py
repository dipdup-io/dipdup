from typing import Literal

from eth_utils.address import is_address
from eth_utils.address import to_normalized_address
from pydantic import validator
from pydantic.dataclasses import dataclass

from dipdup.config import ContractConfig
from dipdup.exceptions import ConfigurationError

EVM_ADDRESS_PREFIXES = ('0x',)
EVM_ADDRESS_LENGTH = 42


@dataclass
class EvmContractConfig(ContractConfig):
    """EVM contract config

    :param kind: Always `evm`
    :param address: Contract address
    :param abi: ABI or topic0
    :param typename: Alias for the contract script
    """

    kind: Literal['evm']
    address: str | None = None
    # FIXME: Or topic0?
    abi: str | None = None
    typename: str | None = None

    @validator('address', allow_reuse=True)
    def _valid_address(cls, v: str | None) -> str | None:
        # NOTE: It's a `config export` call with environment variable substitution disabled
        if not v or '$' in v:
            return v

        if not is_address(v):
            raise ConfigurationError(f'{v} is not a valid EVM contract address')
        # NOTE: Normalizing is converting address to a non-checksum form.
        # See https://coincodex.com/article/2078/ethereum-address-checksum-explained/
        return to_normalized_address(v)

    def get_address(self) -> str:
        if self.address is None:
            raise ConfigurationError(f'`contracts.{self.name}`: `address` field is required`')
        return self.address
