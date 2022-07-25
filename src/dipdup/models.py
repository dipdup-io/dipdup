import logging
from collections import defaultdict
from copy import copy
from dataclasses import field
from datetime import date
from datetime import datetime
from datetime import time
from decimal import Decimal
from enum import Enum
from functools import cache
from typing import Any
from typing import DefaultDict
from typing import Deque
from typing import Dict
from typing import Generic
from typing import Iterable
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import cast

from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from tortoise import BaseDBAsyncClient
from tortoise import Model as TortoiseModel
from tortoise import fields
from tortoise.expressions import Q
from tortoise.fields import relational
from tortoise.models import MODEL
from tortoise.queryset import BulkCreateQuery as TortoiseBulkCreateQuery
from tortoise.queryset import BulkUpdateQuery as TortoiseBulkUpdateQuery
from tortoise.queryset import DeleteQuery as TortoiseDeleteQuery
from tortoise.queryset import QuerySet as TortoiseQuerySet
from tortoise.queryset import UpdateQuery as TortoiseUpdateQuery

from dipdup.enums import IndexStatus
from dipdup.enums import IndexType
from dipdup.enums import ReindexingReason
from dipdup.enums import TokenStandard
from dipdup.utils import json_dumps

ParameterType = TypeVar('ParameterType', bound=BaseModel)
StorageType = TypeVar('StorageType', bound=BaseModel)
KeyType = TypeVar('KeyType', bound=BaseModel)
ValueType = TypeVar('ValueType', bound=BaseModel)


_logger = logging.getLogger(__name__)

# ===> Dataclasses


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
    diffs: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)
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
    originated_contract_tzips: Optional[Tuple[str, ...]] = None
    delegate_address: Optional[str] = None
    delegate_alias: Optional[str] = None


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
    metadata: Optional[Dict[str, Any]] = None
    from_alias: Optional[str] = None
    from_address: Optional[str] = None
    to_alias: Optional[str] = None
    to_address: Optional[str] = None
    amount: Optional[int] = None
    tzkt_transaction_id: Optional[int] = None
    tzkt_origination_id: Optional[int] = None
    tzkt_migration_id: Optional[int] = None


# ===> Model Versioning


versioned_fields: DefaultDict[str, Set[str]] = defaultdict(set)


@dataclass
class VersionedTransaction:
    """Metadata of currently opened versioned transaction."""

    level: int
    index: str
    immune_tables: Set[str]


# NOTE: Overwritten by TransactionManager.register()
def get_transaction() -> Optional[VersionedTransaction]:
    """Get metadata of currently opened versioned transaction if any"""
    raise RuntimeError('TransactionManager is not registered')


# NOTE: Overwritten by TransactionManager.register()
def get_pending_updates() -> Deque['ModelUpdate']:
    """Get pending model updates queue"""
    raise RuntimeError('TransactionManager is not registered')


class ModelUpdateAction(Enum):
    """Mapping for actions in model update"""

    INSERT = 'INSERT'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'


class ModelUpdate(TortoiseModel):
    """Model update created within versioned transactions"""

    model_name = fields.CharField(256)
    model_pk = fields.CharField(256)
    level = fields.IntField()
    index = fields.CharField(256)

    action = fields.CharEnumField(ModelUpdateAction)
    data: Dict[str, Any] = fields.JSONField(encoder=json_dumps, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_model_update'

    @classmethod
    def from_model(cls, model: 'Model', action: ModelUpdateAction) -> Optional['ModelUpdate']:
        """Create model update from model instance if necessary"""
        if not (transaction := get_transaction()):
            return None
        if model._meta.db_table in transaction.immune_tables:
            return None

        if action == ModelUpdateAction.INSERT:
            data = None
        elif action == ModelUpdateAction.UPDATE:
            data = model.versioned_data_diff
            if not data:
                return None
        elif action == ModelUpdateAction.DELETE:
            data = model.versioned_data
        else:
            raise ValueError(f'Unknown action: {action}')

        self = ModelUpdate(
            model_name=model.__class__.__name__,
            model_pk=model.pk,
            level=transaction.level,
            index=transaction.index,
            action=action,
            data=data,
        )
        _logger.debug(
            'Saving %s(%s) %s: %s',
            self.model_name,
            self.model_pk,
            self.action.value,
            data,
        )
        return self

    async def revert(self, model: Type[TortoiseModel]) -> None:
        """Revert a single model update"""
        data = copy(self.data)
        # NOTE: Deserialize non-JSON types
        if data:
            for key, field_ in model._meta.fields_map.items():
                # NOTE: Restore deleted models with old PK
                if field_.pk and self.action == ModelUpdateAction.DELETE:
                    data[key] = self.model_pk
                    continue

                value = data.get(key)
                if value is None:
                    continue

                if isinstance(field_, fields.DecimalField):
                    data[key] = Decimal(value)
                elif isinstance(field_, fields.DatetimeField):
                    data[key] = datetime.fromisoformat(value)
                elif isinstance(field_, fields.DateField):
                    data[key] = date.fromisoformat(value)
                elif isinstance(field_, fields.TimeField):
                    data[key] = time.fromisoformat(value)

                # TODO: There may be more non-JSON-deserializable fields

        _logger.debug(
            'Reverting %s(%s) %s: %s',
            self.model_name,
            self.model_pk,
            self.action.value,
            data,
        )
        # NOTE: Do not version rollbacks, use unpatched querysets
        if self.action == ModelUpdateAction.INSERT:
            await TortoiseQuerySet(model).filter(pk=self.model_pk).delete()
        elif self.action == ModelUpdateAction.UPDATE:
            await TortoiseQuerySet(model).filter(pk=self.model_pk).update(**data)
        elif self.action == ModelUpdateAction.DELETE:
            await model.create(**data)

        await self.delete()


class UpdateQuery(TortoiseUpdateQuery):
    def __init__(
        self,
        model: Type[TortoiseModel],
        update_kwargs: Dict[str, Any],
        db: BaseDBAsyncClient,
        q_objects: List[Q],
        annotations: Dict[str, Any],
        custom_filters: Dict[str, Dict[str, Any]],
        limit: Optional[int],
        orderings: List[Tuple[str, str]],
        filter_queryset: TortoiseQuerySet,
    ) -> None:
        super().__init__(
            model,
            update_kwargs,
            db,
            q_objects,
            annotations,
            custom_filters,
            limit,
            orderings,
        )
        self.filter_queryset = filter_queryset

    async def _execute(self) -> int:
        _logger.debug('Prefetching query models: %s', self.filter_queryset)
        models = await self.filter_queryset
        _logger.debug('Got %s', len(models))

        for model in models:
            model._set_kwargs(self.update_kwargs)
            if update := ModelUpdate.from_model(model, ModelUpdateAction.UPDATE):
                get_pending_updates().append(update)

        return await super()._execute()


class DeleteQuery(TortoiseDeleteQuery):
    def __init__(
        self,
        model: Type[TortoiseModel],
        db: BaseDBAsyncClient,
        q_objects: List[Q],
        annotations: Dict[str, Any],
        custom_filters: Dict[str, Dict[str, Any]],
        limit: Optional[int],
        orderings: List[Tuple[str, str]],
        filter_queryset: TortoiseQuerySet,
    ) -> None:
        super().__init__(model, db, q_objects, annotations, custom_filters, limit, orderings)
        self.filter_queryset = filter_queryset

    async def _execute(self) -> int:
        _logger.debug('Prefetching query models: %s', self.filter_queryset)
        models = await self.filter_queryset
        _logger.debug('Got %s', len(models))

        for model in models:
            if update := ModelUpdate.from_model(model, ModelUpdateAction.DELETE):
                get_pending_updates().append(update)

        return await super()._execute()


class BulkUpdateQuery(TortoiseBulkUpdateQuery):
    async def _execute(self) -> int:
        for model in self.objects:
            if update := ModelUpdate.from_model(
                cast(Model, model),
                ModelUpdateAction.UPDATE,
            ):
                get_pending_updates().append(update)

        return await super()._execute()


class BulkCreateQuery(TortoiseBulkCreateQuery):
    async def _execute(self) -> List[MODEL]:
        for model in self.objects:
            if update := ModelUpdate.from_model(
                cast(Model, model),
                ModelUpdateAction.INSERT,
            ):
                get_pending_updates().append(update)

        return await super()._execute()


class QuerySet(TortoiseQuerySet):
    def update(self, **kwargs: Any) -> UpdateQuery:
        return UpdateQuery(
            db=self._db,
            model=self.model,
            update_kwargs=kwargs,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            limit=self._limit,
            orderings=self._orderings,
            filter_queryset=self,
        )

    def delete(self) -> DeleteQuery:
        return DeleteQuery(
            db=self._db,
            model=self.model,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            limit=self._limit,
            orderings=self._orderings,
            filter_queryset=self,
        )


@cache
def get_versioned_fields(model: Type['Model']) -> Set[str]:
    field_names: Set[str] = set()
    field_keys = model._meta.db_fields.union(model._meta.fk_fields)

    for key, field_ in model._meta.fields_map.items():
        if key not in field_keys:
            continue
        if field_.pk:
            continue
        elif isinstance(field_, relational.ForeignKeyFieldInstance):
            field_names.add(f'{key}_id')
        else:
            field_names.add(key)

    return field_names


class Model(TortoiseModel):
    """Base class for DipDup project models"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._original_versioned_data = self.versioned_data

    @classmethod
    def _init_from_db(cls, **kwargs: Any) -> 'Model':
        model = super()._init_from_db(**kwargs)
        model._original_versioned_data = model.versioned_data
        return model

    @property
    def original_versioned_data(self) -> Dict[str, Any]:
        """Get versioned data of the model at the time of creation"""
        return self._original_versioned_data

    @property
    def versioned_data(self) -> Dict[str, Any]:
        """Get versioned data of the model at the current time"""
        return {name: getattr(self, name) for name in get_versioned_fields(self.__class__)}

    @property
    def versioned_data_diff(self) -> Dict[str, Any]:
        """Get versioned data of the model changed since creation"""
        data = {}
        for key, value in self.original_versioned_data.items():
            if value != self.versioned_data[key]:
                data[key] = value
        return data

    # NOTE: Do not touch docstrings below this line to preserve Tortoise ones
    async def delete(
        self,
        using_db: Optional[BaseDBAsyncClient] = None,
    ) -> None:
        await super().delete(using_db=using_db)

        if update := ModelUpdate.from_model(self, ModelUpdateAction.DELETE):
            get_pending_updates().append(update)

    async def save(
        self,
        using_db: Optional[BaseDBAsyncClient] = None,
        update_fields: Optional[Iterable[str]] = None,
        force_create: bool = False,
        force_update: bool = False,
    ) -> None:
        action = ModelUpdateAction.UPDATE if self._saved_in_db else ModelUpdateAction.INSERT
        await super().save(
            using_db=using_db,
            update_fields=update_fields,
            force_create=force_create,
            force_update=force_update,
        )

        if update := ModelUpdate.from_model(self, action):
            get_pending_updates().append(update)

    @classmethod
    def filter(cls, *args: Any, **kwargs: Any) -> TortoiseQuerySet:
        return QuerySet(cls).filter(*args, **kwargs)

    @classmethod
    async def create(
        cls: Type['ModelT'],
        using_db: Optional[BaseDBAsyncClient] = None,
        **kwargs: Any,
    ) -> 'ModelT':
        instance = cls(**kwargs)
        instance._saved_in_db = False
        db = using_db or cls._choose_db(True)
        await instance.save(using_db=db, force_create=True)
        return instance

    @classmethod
    def bulk_create(
        cls: Type['Model'],
        objects: Iterable['Model'],
        batch_size: Optional[int] = None,
        ignore_conflicts: bool = False,
        update_fields: Optional[Iterable[str]] = None,
        on_conflict: Optional[Iterable[str]] = None,
        using_db: Optional[BaseDBAsyncClient] = None,
    ) -> BulkCreateQuery:
        if ignore_conflicts and update_fields:
            raise ValueError(
                "ignore_conflicts and update_fields are mutually exclusive.",
            )
        if not ignore_conflicts:
            if (update_fields and not on_conflict) or (on_conflict and not update_fields):
                raise ValueError("update_fields and on_conflict need set in same time.")

        return BulkCreateQuery(
            db=using_db or cls._choose_db(True),
            model=cls,
            objects=objects,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
            update_fields=update_fields,
            on_conflict=on_conflict,
        )

    @classmethod
    def bulk_update(
        cls: Type['Model'],
        objects: Iterable['Model'],
        fields: Iterable[str],
        batch_size: Optional[int] = None,
        using_db: Optional[BaseDBAsyncClient] = None,
    ) -> BulkUpdateQuery:
        if any(obj.pk is None for obj in objects):
            raise ValueError("All bulk_update() objects must have a primary key set.")

        self = QuerySet(cls)
        return BulkUpdateQuery(  # type:ignore
            db=self._db,
            model=self.model,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            limit=self._limit,
            orderings=self._orderings,
            objects=objects,
            fields=fields,
            batch_size=batch_size,
        )

    class Meta:
        abstract = True


ModelT = TypeVar('ModelT', bound=Model)


# ===> Built-in Models (not versioned)


class Schema(TortoiseModel):
    name = fields.CharField(256, pk=True)
    hash = fields.CharField(256)
    reindex = fields.CharEnumField(ReindexingReason, max_length=40, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_schema'


class Head(TortoiseModel):
    name = fields.CharField(256, pk=True)
    level = fields.IntField()
    hash = fields.CharField(64)
    timestamp = fields.DatetimeField()

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_head'


class Index(TortoiseModel):
    name = fields.CharField(256, pk=True)
    type = fields.CharEnumField(IndexType)
    status = fields.CharEnumField(IndexStatus, default=IndexStatus.NEW)

    config_hash = fields.CharField(256)
    template = fields.CharField(256, null=True)
    template_values: Dict[str, Any] = fields.JSONField(null=True)

    level = fields.IntField(default=0)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    async def update_status(
        self,
        status: Optional[IndexStatus] = None,
        level: Optional[int] = None,
    ) -> None:
        self.status = status or self.status
        self.level = level or self.level
        await self.save()

    class Meta:
        table = 'dipdup_index'


class Contract(TortoiseModel):
    name = fields.CharField(256, pk=True)
    address = fields.CharField(256)
    typename = fields.CharField(256, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_contract'


# ===> Built-in Models (versioned)


class ContractMetadata(Model):
    network = fields.CharField(51)
    contract = fields.CharField(36)
    metadata = fields.JSONField()
    update_id = fields.IntField()

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_contract_metadata'
        unique_together = ('network', 'contract')


class TokenMetadata(Model):
    network = fields.CharField(51)
    contract = fields.CharField(36)
    token_id = fields.TextField()
    metadata = fields.JSONField()
    update_id = fields.IntField()

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_token_metadata'
        unique_together = ('network', 'contract', 'token_id')
