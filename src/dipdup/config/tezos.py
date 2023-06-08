from typing import Literal

from pydantic import validator
from pydantic.dataclasses import dataclass

from dipdup.config import ContractConfig
from dipdup.exceptions import ConfigurationError

TEZOS_ADDRESS_PREFIXES = (
    'KT1',
    # NOTE: Wallet addresses are allowed during config validation for debugging purposes.
    # NOTE: It's a undocumented hack to filter by `source` field. Wallet indexing is not supported.
    # NOTE: See https://github.com/dipdup-io/dipdup/issues/291
    'tz1',
    'tz2',
    'tz3',
)
TEZOS_ADDRESS_LENGTH = 36


@dataclass
class TezosContractConfig(ContractConfig):
    """Contract config

    :param address: Contract address
    :param code_hash: Contract code hash or address to fetch it from
    :param typename: Alias for the contract script
    """

    kind: Literal['tezos']
    typename: str | None = None
    address: str | None = None
    code_hash: int | str | None = None

    @validator('address', allow_reuse=True)
    def _valid_address(cls, v: str | None) -> str | None:
        # NOTE: It's a `config export` call with environment variable substitution disabled
        if not v or '$' in v:
            return v

        if not v.startswith(TEZOS_ADDRESS_PREFIXES) or len(v) != TEZOS_ADDRESS_LENGTH:
            raise ValueError(f'`{v}` is not a valid Tezos address')

        return v

    def get_address(self) -> str:
        if self.address is None:
            raise ConfigurationError(f'`contracts.{self.name}`: `address` field is required`')
        return self.address
