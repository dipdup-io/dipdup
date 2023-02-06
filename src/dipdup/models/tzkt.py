from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from typing import Generic
from typing import Literal
from typing import Optional
from typing import TypeVar

from pydantic import BaseModel
from pydantic import Field
from pydantic.dataclasses import dataclass

from dipdup.exceptions import FrameworkException
from dipdup.subscriptions import Subscription

ParameterType = TypeVar('ParameterType', bound=BaseModel)
StorageType = TypeVar('StorageType', bound=BaseModel)
KeyType = TypeVar('KeyType', bound=BaseModel)
ValueType = TypeVar('ValueType', bound=BaseModel)
EventType = TypeVar('EventType', bound=BaseModel)


class TokenStandard(Enum):
    FA12 = 'fa1.2'
    FA2 = 'fa2'


class OperationType(Enum):
    """Type of blockchain operation"""

    transaction = 'transaction'
    origination = 'origination'
    migration = 'migration'


class MessageType(Enum):
    """Enum for realtime message types"""

    operation = 'operation'
    big_map = 'big_map'
    head = 'head'
    token_transfer = 'token_transfer'
    event = 'event'


@dataclass(frozen=True)
class HeadSubscription(Subscription):
    type: Literal['head'] = 'head'
    method: Literal['SubscribeToHead'] = 'SubscribeToHead'

    def get_request(self) -> list[dict[str, str]]:
        return []


@dataclass(frozen=True)
class OriginationSubscription(Subscription):
    type: Literal['origination'] = 'origination'
    method: Literal['SubscribeToOperations'] = 'SubscribeToOperations'

    def get_request(self) -> list[dict[str, Any]]:
        return [{'types': 'origination'}]


@dataclass(frozen=True)
class TransactionSubscription(Subscription):
    type: Literal['transaction'] = 'transaction'
    method: Literal['SubscribeToOperations'] = 'SubscribeToOperations'
    address: str | None = None

    def get_request(self) -> list[dict[str, Any]]:
        request: dict[str, Any] = {'types': 'transaction'}
        if self.address:
            request['address'] = self.address
        return [request]


# TODO: Add `ptr` and `tags` filters?
@dataclass(frozen=True)
class BigMapSubscription(Subscription):
    type: Literal['big_map'] = 'big_map'
    method: Literal['SubscribeToBigMaps'] = 'SubscribeToBigMaps'
    address: str | None = None
    path: str | None = None

    def get_request(self) -> list[dict[str, Any]]:
        if self.address and self.path:
            return [{'address': self.address, 'paths': [self.path]}]
        elif not self.address and not self.path:
            return [{}]
        else:
            raise FrameworkException('Either both `address` and `path` should be set or none of them')


@dataclass(frozen=True)
class TokenTransferSubscription(Subscription):
    type: Literal['token_transfer'] = 'token_transfer'
    method: Literal['SubscribeToTokenTransfers'] = 'SubscribeToTokenTransfers'
    contract: str | None = None
    token_id: int | None = None
    from_: str | None = Field(None, alias='from')
    to: str | None = None

    def get_request(self) -> list[dict[str, Any]]:
        request: dict[str, Any] = {}
        if self.token_id:
            request['token_id'] = self.token_id
        if self.contract:
            request['contract'] = self.contract
        if self.from_:
            request['from'] = self.from_
        if self.to:
            request['to'] = self.to
        return [request]


@dataclass(frozen=True)
class EventSubscription(Subscription):
    type: Literal['event'] = 'event'
    method: Literal['SubscribeToEvents'] = 'SubscribeToEvents'
    address: str | None = None

    def get_request(self) -> list[dict[str, Any]]:
        if self.address:
            return [{'address': self.address}]

        return [{}]


@dataclass
class OperationData:
    """Basic structure for operations from TzKT response"""

    type: str
    id: int
    level: int
    timestamp: datetime
    hash: str
    counter: int
    sender_address: Optional[str]
    target_address: Optional[str]
    initiator_address: Optional[str]
    amount: Optional[int]
    status: str
    has_internals: Optional[bool]
    storage: Any
    diffs: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    block: Optional[str] = None
    sender_alias: Optional[str] = None
    nonce: Optional[int] = None
    target_alias: Optional[str] = None
    initiator_alias: Optional[str] = None
    entrypoint: Optional[str] = None
    parameter_json: Optional[Any] = None
    originated_contract_address: Optional[str] = None
    originated_contract_alias: Optional[str] = None
    originated_contract_type_hash: Optional[int] = None
    originated_contract_code_hash: Optional[int] = None
    originated_contract_tzips: Optional[tuple[str, ...]] = None
    delegate_address: Optional[str] = None
    delegate_alias: Optional[str] = None
    target_code_hash: Optional[int] = None
    sender_code_hash: Optional[int] = None


@dataclass
class Transaction(Generic[ParameterType, StorageType]):
    """Wrapper for matched transaction with typed data passed to the handler"""

    data: OperationData
    parameter: ParameterType
    storage: StorageType


@dataclass
class Origination(Generic[StorageType]):
    """Wrapper for matched origination with typed data passed to the handler"""

    data: OperationData
    storage: StorageType


class BigMapAction(Enum):
    """Mapping for action in TzKT response"""

    ALLOCATE = 'allocate'
    ADD_KEY = 'add_key'
    UPDATE_KEY = 'update_key'
    REMOVE_KEY = 'remove_key'
    REMOVE = 'remove'

    @property
    def has_key(self) -> bool:
        return self in (BigMapAction.ADD_KEY, BigMapAction.UPDATE_KEY, BigMapAction.REMOVE_KEY)

    @property
    def has_value(self) -> bool:
        return self in (BigMapAction.ADD_KEY, BigMapAction.UPDATE_KEY)


@dataclass
class BigMapData:
    """Basic structure for big map diffs from TzKT response"""

    id: int
    level: int
    operation_id: int
    timestamp: datetime
    bigmap: int
    contract_address: str
    path: str
    action: BigMapAction
    active: bool
    key: Optional[Any] = None
    value: Optional[Any] = None


@dataclass
class BigMapDiff(Generic[KeyType, ValueType]):
    """Wrapper for matched big map diff with typed data passed to the handler"""

    action: BigMapAction
    data: BigMapData
    key: Optional[KeyType]
    value: Optional[ValueType]


@dataclass
class BlockData:
    """Basic structure for blocks received from TzKT REST API"""

    level: int
    hash: str
    timestamp: datetime
    proto: int
    validations: int
    deposit: int
    reward: int
    fees: int
    nonce_revealed: bool
    priority: Optional[int] = None
    baker_address: Optional[str] = None
    baker_alias: Optional[str] = None


@dataclass
class HeadBlockData:
    """Basic structure for head block received from TzKT SignalR API"""

    chain: str
    chain_id: str
    cycle: int
    level: int
    hash: str
    protocol: str
    next_protocol: str
    timestamp: datetime
    voting_epoch: int
    voting_period: int
    known_level: int
    last_sync: datetime
    synced: bool
    quote_level: int
    quote_btc: Decimal
    quote_eur: Decimal
    quote_usd: Decimal
    quote_cny: Decimal
    quote_jpy: Decimal
    quote_krw: Decimal
    quote_eth: Decimal
    quote_gbp: Decimal


@dataclass
class QuoteData:
    """Basic structure for quotes received from TzKT REST API"""

    level: int
    timestamp: datetime
    btc: Decimal
    eur: Decimal
    usd: Decimal
    cny: Decimal
    jpy: Decimal
    krw: Decimal
    eth: Decimal
    gbp: Decimal


@dataclass
class TokenTransferData:
    """Basic structure for token transver received from TzKT SignalR API"""

    id: int
    level: int
    timestamp: datetime
    tzkt_token_id: int
    contract_address: Optional[str] = None
    contract_alias: Optional[str] = None
    token_id: Optional[int] = None
    standard: Optional[TokenStandard] = None
    metadata: Optional[dict[str, Any]] = None
    from_alias: Optional[str] = None
    from_address: Optional[str] = None
    to_alias: Optional[str] = None
    to_address: Optional[str] = None
    amount: Optional[int] = None
    tzkt_transaction_id: Optional[int] = None
    tzkt_origination_id: Optional[int] = None
    tzkt_migration_id: Optional[int] = None


@dataclass
class EventData:
    """Basic structure for events received from TzKT REST API"""

    id: int
    level: int
    timestamp: datetime
    tag: str
    payload: Any | None
    contract_address: str
    contract_alias: Optional[str] = None
    contract_code_hash: Optional[int] = None
    transaction_id: Optional[int] = None


@dataclass
class Event(Generic[EventType]):
    data: EventData
    payload: EventType


@dataclass
class UnknownEvent:
    data: EventData
    payload: Any | None
