from contextlib import suppress
from datetime import datetime
from decimal import Decimal
from enum import Enum
from functools import lru_cache
from itertools import groupby
from typing import Any
from typing import Generic
from typing import Hashable
from typing import Iterable
from typing import Literal
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import Union
from typing import cast
from typing import get_args
from typing import get_origin

from pydantic import BaseModel
from pydantic import Extra
from pydantic import Field
from pydantic.dataclasses import dataclass

from dipdup.enums import TokenStandard
from dipdup.exceptions import FrameworkException
from dipdup.exceptions import InvalidDataError
from dipdup.subscriptions import Subscription
from dipdup.utils.codegen import parse_object

ParameterType = TypeVar('ParameterType', bound=BaseModel)
StorageType = TypeVar('StorageType', bound=BaseModel)
KeyType = TypeVar('KeyType', bound=BaseModel)
ValueType = TypeVar('ValueType', bound=BaseModel)
EventType = TypeVar('EventType', bound=BaseModel)


IntrospectionError = (KeyError, IndexError, AttributeError)

T = TypeVar('T', Hashable, Type[BaseModel])


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


def extract_root_outer_type(storage_type: Type[BaseModel]) -> T:
    """Extract Pydantic __root__ type"""
    root_field = storage_type.__fields__['__root__']
    if root_field.allow_none:
        # NOTE: Optional is a magic _SpecialForm
        return cast(Type[BaseModel], Optional[root_field.type_])

    return root_field.outer_type_  # type: ignore[no-any-return]


# FIXME: Unsafe cache size here and below
@lru_cache(None)
def is_array_type(storage_type: type[Any]) -> bool:
    """TzKT can return bigmaps as objects or as arrays of key-value objects. Guess it from storage type."""
    # NOTE: list[...]
    if get_origin(storage_type) == list:
        return True

    # NOTE: Pydantic model with __root__ field subclassing List
    with suppress(*IntrospectionError):
        root_type = extract_root_outer_type(storage_type)
        return is_array_type(root_type)

    # NOTE: Something else
    return False


@lru_cache(None)
def get_list_elt_type(list_type: Type[Any]) -> Type[Any]:
    """Extract list item type from list type"""
    # NOTE: regular list
    if get_origin(list_type) == list:
        return get_args(list_type)[0]  # type: ignore[no-any-return]

    # NOTE: Pydantic model with __root__ field subclassing List
    root_type = extract_root_outer_type(list_type)
    return get_list_elt_type(root_type)


@lru_cache(None)
def get_dict_value_type(dict_type: Type[Any], key: str | None = None) -> Type[Any]:
    """Extract dict value types from field type"""
    # NOTE: Regular dict
    if get_origin(dict_type) == dict:
        return get_args(dict_type)[1]  # type: ignore[no-any-return]

    # NOTE: Pydantic model with __root__ field subclassing Dict
    with suppress(*IntrospectionError):
        root_type = extract_root_outer_type(dict_type)
        return get_dict_value_type(root_type, key)

    if key is None:
        raise KeyError('Field name or alias is required for object introspection')

    # NOTE: Pydantic model, find corresponding field and return it's type
    fields = dict_type.__fields__
    for field in fields.values():
        if key in (field.name, field.alias):
            # NOTE: Pydantic does not preserve outer_type_ for Optional
            if field.allow_none:
                return cast(Type[Any], Optional[field.type_])
            else:
                return field.outer_type_  # type: ignore[no-any-return]

    # NOTE: Either we try the wrong Union path or model was modifier by user
    raise KeyError(f'Field `{key}` not found in {dict_type}')


@lru_cache(None)
def unwrap_union_type(union_type: type[Any]) -> tuple[bool, tuple[type[Any], ...]]:
    """Check if the type is either optional or union and return arg types if so"""
    if get_origin(union_type) == Union:
        return True, get_args(union_type)

    with suppress(*IntrospectionError):
        root_type = extract_root_outer_type(union_type)
        return unwrap_union_type(root_type)

    return False, ()


def _preprocess_bigmap_diffs(diffs: Iterable[dict[str, Any]]) -> dict[int, Iterable[dict[str, Any]]]:
    """Filter out bigmap diffs and group them by bigmap id"""
    return {
        k: tuple(v)
        for k, v in groupby(
            filter(lambda d: d['action'] in ('add_key', 'update_key'), diffs),
            lambda d: cast(int, d['bigmap']),
        )
    }


def _apply_bigmap_diffs(
    bigmap_id: int,
    bigmap_diffs: dict[int, Iterable[dict[str, Any]]],
    is_array: bool,
) -> Union[list[dict[str, Any]], dict[str, Any]]:
    """Apply bigmap diffs to the storage"""
    diffs = bigmap_diffs.get(bigmap_id, ())
    diffs_items = ((d['content']['key'], d['content']['value']) for d in diffs)

    if is_array:
        list_storage: list[dict[str, Any]] = []
        for key, value in diffs_items:
            list_storage.append({'key': key, 'value': value})
        return list_storage

    else:
        dict_storage: dict[str, Any] = {}
        for key, value in diffs_items:
            dict_storage[key] = value
        return dict_storage


def _process_storage(storage: Any, storage_type: T, bigmap_diffs: dict[int, Iterable[dict[str, Any]]]) -> Any:
    """Replace bigmap pointers with actual data from diffs"""
    # NOTE: First, check if the type is a Union. Remember, Optional is a Union too.
    is_union, arg_types = unwrap_union_type(storage_type)
    if is_union:
        # NOTE: We have no way but trying every possible branch until first success
        for arg_type in arg_types:
            with suppress(*IntrospectionError):
                return _process_storage(storage, arg_type, bigmap_diffs)

    # NOTE: Value is a bigmap pointer; apply diffs according to array type
    if isinstance(storage, int) and type(storage) != storage_type:
        is_array = is_array_type(storage_type)
        storage = _apply_bigmap_diffs(storage, bigmap_diffs, is_array)

    # NOTE: List, process recursively
    elif isinstance(storage, list):
        elt_type = get_list_elt_type(storage_type)
        for i, _ in enumerate(storage):
            storage[i] = _process_storage(storage[i], elt_type, bigmap_diffs)

    # NOTE: Dict, process recursively
    elif isinstance(storage, dict):
        # NOTE: Ignore missing fields along with extra ones
        ignore = getattr(getattr(storage_type, 'Config', None), 'extra', None) == Extra.ignore

        for key, value in storage.items():
            try:
                value_type = get_dict_value_type(storage_type, key)
                storage[key] = _process_storage(value, value_type, bigmap_diffs)
            except IntrospectionError:
                if not ignore:
                    raise
    # NOTE: Leave others untouched
    else:
        pass

    return storage


def deserialize_storage(operation_data: OperationData, storage_type: Type[StorageType]) -> StorageType:
    """Merge big map diffs and deserialize raw storage into typeclass"""
    bigmap_diffs = _preprocess_bigmap_diffs(operation_data.diffs)

    try:
        operation_data.storage = _process_storage(
            storage=operation_data.storage,
            storage_type=storage_type,
            bigmap_diffs=bigmap_diffs,
        )
        return parse_object(storage_type, operation_data.storage)
    except IntrospectionError as e:
        raise InvalidDataError(e.args[0], storage_type, operation_data.storage) from e
