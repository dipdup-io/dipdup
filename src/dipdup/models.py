import logging
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from pydantic.error_wrappers import ValidationError
from tortoise import Model, fields

from dipdup.exceptions import ConfigurationError, DipDupException, InvalidDataError

ParameterType = TypeVar('ParameterType', bound=BaseModel)
StorageType = TypeVar('StorageType', bound=BaseModel)
KeyType = TypeVar('KeyType', bound=BaseModel)
ValueType = TypeVar('ValueType', bound=BaseModel)


_logger = logging.getLogger('dipdup.models')


class IndexType(Enum):
    operation = 'operation'
    big_map = 'big_map'


class IndexStatus(Enum):
    NEW = 'NEW'
    SYNCING = 'SYNCING'
    REALTIME = 'REALTIME'
    ROLLBACK = 'ROLLBACK'
    ONESHOT = 'ONESHOT'


@dataclass
class OperationData:
    """Basic structure for operations from TzKT response"""

    type: str
    id: int
    level: int
    timestamp: datetime
    hash: str
    counter: int
    sender_address: str
    target_address: Optional[str]
    initiator_address: Optional[str]
    amount: Optional[int]
    status: str
    has_internals: Optional[bool]
    storage: Dict[str, Any]
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
    diffs: Optional[List[Dict[str, Any]]] = None

    # TODO: Refactor this class, move storage processing methods to TzktDatasource
    def _merge_bigmapdiffs(self, storage_dict: Dict[str, Any], bigmap_name: str, array: bool) -> None:
        """Apply big map diffs of specific path to storage"""
        if self.diffs is None:
            raise Exception('`bigmaps` field missing')
        _logger.debug(bigmap_name)
        bigmapdiffs = [bm for bm in self.diffs if bm['path'] == bigmap_name]
        bigmap_key = bigmap_name.split('.')[-1]
        for diff in bigmapdiffs:
            _logger.debug('Applying bigmapdiff: %s', diff)
            if diff['action'] in ('add_key', 'update_key'):
                key = diff['content']['key']
                if array is True:
                    storage_dict[bigmap_key].append({'key': key, 'value': diff['content']['value']})
                else:
                    storage_dict[bigmap_key][key] = diff['content']['value']

    def _process_storage(
        self,
        storage_type: Type[StorageType],
        storage: Dict[str, Any],
        prefix: str = None,
    ) -> Dict[str, Any]:
        for key, field in storage_type.__fields__.items():

            if key == '__root__':
                continue

            if field.alias:
                key = field.alias

            bigmap_name = key if prefix is None else f'{prefix}.{key}'

            # NOTE: TzKT could return bigmaps as object or as array of key-value objects. We need to guess this from storage.
            # TODO: This code should be a part of datasource module.
            try:
                value = storage[key]
            except KeyError as e:
                if not field.required:
                    continue
                raise ConfigurationError(f'Type `{storage_type.__name__}` is invalid: `{key}` field does not exists') from e

            # FIXME: Pydantic bug. `BaseModel.type_` returns incorrect value when annotation is Dict[str, bool]
            if field.type_ != field.outer_type_ and field.type_ == bool:
                annotation = field.outer_type_
            else:
                annotation = field.type_

            if annotation not in (int, bool) and isinstance(value, int):
                if hasattr(annotation, '__fields__') and 'key' in annotation.__fields__ and 'value' in annotation.__fields__:
                    storage[key] = []
                    if self.diffs:
                        self._merge_bigmapdiffs(storage, bigmap_name, array=True)
                else:
                    storage[key] = {}
                    if self.diffs:
                        self._merge_bigmapdiffs(storage, bigmap_name, array=False)
            elif hasattr(annotation, '__fields__') and isinstance(storage[key], dict):
                storage[key] = self._process_storage(annotation, storage[key], bigmap_name)

        return storage

    def get_merged_storage(self, storage_type: Type[StorageType]) -> StorageType:
        """Merge big map diffs and deserialize raw storage into typeclass"""
        if self.storage is None:
            raise Exception('`storage` field missing')

        storage = deepcopy(self.storage)
        _logger.debug('Merging storage')
        _logger.debug('Before: %s', storage)
        _logger.debug('Diffs: %s', self.diffs)

        storage = self._process_storage(storage_type, storage, None)

        _logger.debug('After: %s', storage)

        try:
            return storage_type.parse_obj(storage)
        except ValidationError as e:
            raise InvalidDataError(storage_type, storage, self) from e


@dataclass
class Transaction(Generic[ParameterType, StorageType]):
    """Wrapper for every transaction in handler arguments"""

    data: OperationData
    parameter: ParameterType
    storage: StorageType


@dataclass
class Origination(Generic[StorageType]):
    """Wrapper for every origination in handler arguments"""

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
    key: Optional[Any] = None
    value: Optional[Any] = None


@dataclass
class BigMapDiff(Generic[KeyType, ValueType]):
    """Wrapper for every big map diff in handler arguments"""

    action: BigMapAction
    data: BigMapData
    key: Optional[KeyType]
    value: Optional[ValueType]


@dataclass
class BlockData:
    """Basic structure for blocks from TzKT HTTP response"""

    level: int
    hash: str
    timestamp: datetime
    proto: int
    priority: int
    validations: int
    deposit: int
    reward: int
    fees: int
    nonce_revealed: bool
    baker_address: Optional[str] = None
    baker_alias: Optional[str] = None


@dataclass
class HeadBlockData:
    """Basic structure for head block from TzKT SignalR response"""

    cycle: int
    level: int
    hash: str
    protocol: str
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


@dataclass
class QuoteData:
    """Basic structure for quotes from TzKT HTTP response"""

    level: int
    timestamp: datetime
    btc: Decimal
    eur: Decimal
    usd: Decimal
    cny: Decimal
    jpy: Decimal
    krw: Decimal
    eth: Decimal


class Schema(Model):
    name = fields.CharField(256, pk=True)
    hash = fields.CharField(256)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_schema'


class Head(Model):
    name = fields.CharField(256, pk=True)
    level = fields.IntField()
    hash = fields.CharField(64)
    timestamp = fields.DatetimeField()

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_head'


class Index(Model):
    name = fields.CharField(256, pk=True)
    type = fields.CharEnumField(IndexType)
    status = fields.CharEnumField(IndexStatus, default=IndexStatus.NEW)

    config_hash = fields.CharField(256)
    template = fields.CharField(256, null=True)
    template_values = fields.JSONField(null=True)

    level = fields.IntField(default=0)
    head = fields.ForeignKeyField('int_models.Head', related_name='indexes', null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    async def update_status(
        self,
        status: IndexStatus,
        level: Optional[int] = None,
        head: Optional['Head'] = None,
    ) -> None:
        if level:
            if level < self.level:
                raise DipDupException('Index level is higher than desired level')
            self.level = level  # type: ignore

        self.head = head
        self.status = status
        await self.save()

    class Meta:
        table = 'dipdup_index'


class Contract(Model):
    name = fields.CharField(256, pk=True)
    address = fields.CharField(256)
    typename = fields.CharField(256, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_contract'
