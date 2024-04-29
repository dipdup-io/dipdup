from abc import ABC
from typing import Literal
from typing import TypeAlias

from eth_utils.address import is_address
from eth_utils.address import to_normalized_address
from pydantic import ConfigDict
from pydantic import field_validator
from pydantic.dataclasses import dataclass

from dipdup.config import Alias
from dipdup.config import ContractConfig
from dipdup.config import Hex
from dipdup.config import IndexConfig
from dipdup.config.abi_etherscan import AbiEtherscanDatasourceConfig
from dipdup.config.evm_node import EvmNodeDatasourceConfig
from dipdup.config.evm_subsquid import EvmSubsquidDatasourceConfig
from dipdup.exceptions import ConfigurationError

EVM_ADDRESS_PREFIXES = ('0x',)
EVM_ADDRESS_LENGTH = 42

EvmDatasourceConfigU: TypeAlias = EvmSubsquidDatasourceConfig | EvmNodeDatasourceConfig | AbiEtherscanDatasourceConfig


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class EvmContractConfig(ContractConfig):
    """EVM contract config

    :param kind: Always `evm`
    :param address: Contract address
    :param abi: Contract ABI
    :param typename: Alias for the contract script
    """

    kind: Literal['evm']
    address: Hex | None = None
    abi: Hex | None = None
    typename: str | None = None

    @field_validator('address', 'abi')
    @classmethod
    def _valid_address(cls, v: str | None) -> str | None:
        # NOTE: It's a `config export` call with environment variable substitution disabled
        if not v or '$' in v:
            return v

        if not is_address(v):
            raise ValueError(f'{v} is not a valid EVM contract address')
        # NOTE: Normalizing is converting address to a non-checksum form.
        # See https://coincodex.com/article/2078/ethereum-address-checksum-explained/
        return to_normalized_address(v)

    def get_address(self) -> str:
        if self.address is None:
            raise ConfigurationError(f'`contracts.{self.name}`: `address` field is required`')
        return self.address


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class EvmIndexConfig(IndexConfig, ABC):
    """EVM index that use Subsquid Network as a datasource

    :param kind: starts with 'evm'
    :param datasources: `evm` datasources to use
    """

    datasources: tuple[Alias[EvmDatasourceConfigU], ...]
