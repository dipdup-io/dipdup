from __future__ import annotations

import re
from abc import ABC
from typing import Literal
from typing import TypeAlias

from pydantic import ConfigDict
from pydantic import field_validator
from pydantic.dataclasses import dataclass

from dipdup.config import Alias
from dipdup.config import ContractConfig
from dipdup.config import IndexConfig
from dipdup.config.starknet_subsquid import StarknetSubsquidDatasourceConfig
from dipdup.exceptions import ConfigurationError

# NOTE: Likely to be extended with ABI and node datasources
StarknetDatasourceConfigU: TypeAlias = StarknetSubsquidDatasourceConfig

_HEX_ADDRESS_REGEXP = re.compile(r'(0x)?[0-9a-f]{1,64}', re.IGNORECASE | re.ASCII)


def is_starknet_address(value: str) -> bool:
    """
    Checks if the given value is a valid StarkNet address within the range [0, 2**251).
    """
    if not isinstance(value, str):
        return False
    if _HEX_ADDRESS_REGEXP.fullmatch(value) is None:
        return False

    # Convert hex to decimal and check if it's less than 2**251
    numeric_value = int(value, 16)
    return numeric_value < 2**251


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class StarknetContractConfig(ContractConfig):
    """Starknet contract config

    :param kind: Always `starknet`
    :param address: Contract address
    :param abi: Contract ABI
    :param typename: Alias for the contract script
    """

    kind: Literal['starknet']
    address: str | None = None
    abi: str | None = None
    typename: str | None = None

    @field_validator('address', 'abi')
    @classmethod
    def _valid_address(cls, value: str | None) -> str | None:
        # NOTE: It's a `config export` call with environment variable substitution disabled
        if not value or '$' in value:
            return value

        if not is_starknet_address(value):
            raise ValueError(f'{value} is not a valid Starknet contract address')

        # TODO: Probably needs to be to normalized as in EVM case
        return value

    def get_address(self) -> str:
        if self.address is None:
            raise ConfigurationError(f'`contracts.{self.name}`: `address` field is required`')
        return self.address


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class StarknetIndexConfig(IndexConfig, ABC):
    """Starknet index that use Subsquid Network as a datasource

    :param datasources: `starknet` datasources to use
    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing and disable this index
    """

    datasources: tuple[Alias[StarknetDatasourceConfigU], ...]

    first_level: int = 0
    last_level: int = 0
