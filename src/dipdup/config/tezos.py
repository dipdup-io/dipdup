from typing import Literal

from pydantic import ConfigDict
from pydantic import field_validator
from pydantic.dataclasses import dataclass

from dipdup.config import ContractConfig
from dipdup.config import IndexConfig
from dipdup.config.tezos_tzkt import TezosTzktDatasourceConfig
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import FrameworkException
from dipdup.models.tezos_tzkt import HeadSubscription
from dipdup.subscriptions import Subscription

ADDRESS_LENGTH = 36
SMART_CONTRACT_PREFIX = 'KT1'
SMART_ROLLUP_PREFIX = 'sr1'
WALLET_PREFIXES = ('tz1', 'tz2', 'tz3')

TezosDatasourceConfigU = TezosTzktDatasourceConfig


def is_contract_address(address: str) -> bool:
    return len(address) == ADDRESS_LENGTH and address.startswith(SMART_CONTRACT_PREFIX)


def is_rollup_address(address: str) -> bool:
    return len(address) == ADDRESS_LENGTH and address.startswith(SMART_ROLLUP_PREFIX)


def is_wallet_address(address: str) -> bool:
    return len(address) == ADDRESS_LENGTH and address.startswith(WALLET_PREFIXES)


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class TezosContractConfig(ContractConfig):
    """Tezos contract config.

    :param kind: Always `tezos`
    :param address: Contract address
    :param code_hash: Contract code hash or address to fetch it from
    :param typename: Alias for the contract script
    """

    kind: Literal['tezos']
    address: str | None = None
    code_hash: int | str | None = None
    typename: str | None = None

    @field_validator('address')
    @classmethod
    def _valid_address(cls, v: str | None) -> str | None:
        # NOTE: It's a `config export` call with environment variable substitution disabled
        if not v or '$' in v:
            return v

        if not any((is_contract_address(v), is_rollup_address(v), is_wallet_address(v))):
            raise ValueError(f'`{v}` is not a valid Tezos address')

        return v

    def get_address(self) -> str:
        if self.address is None:
            raise ConfigurationError(f'`contracts.{self.name}`: `address` field is required`')
        return self.address

    @property
    def resolved_code_hash(self) -> int | None:
        if isinstance(self.code_hash, str):
            raise FrameworkException('`code_hash` was not resolved during startup')
        return self.code_hash


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class TezosIndexConfig(IndexConfig):
    """TzKT index config

    :param kind: starts with 'tezos'
    :param datasources: `tezos` datasources to use
    """

    datasources: tuple[TezosDatasourceConfigU, ...]

    def __post_init__(self) -> None:
        if len(self.datasources) != 1:
            raise ConfigurationError('Tezos indexes currently do not support multiple datasources')
        self.datasource = self.datasources[0]

    def get_subscriptions(self) -> set[Subscription]:
        return {HeadSubscription()}
