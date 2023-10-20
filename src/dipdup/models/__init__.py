from __future__ import annotations

import logging
from contextlib import suppress
from copy import copy
from datetime import date
from datetime import datetime
from datetime import time
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar
from typing import cast

import tortoise
import tortoise.queryset
from pydantic.dataclasses import dataclass
from tortoise.exceptions import OperationalError
from tortoise.fields import relational
from tortoise.models import MODEL
from tortoise.models import Model as TortoiseModel
from tortoise.queryset import BulkCreateQuery as TortoiseBulkCreateQuery
from tortoise.queryset import BulkUpdateQuery as TortoiseBulkUpdateQuery
from tortoise.queryset import DeleteQuery as TortoiseDeleteQuery
from tortoise.queryset import QuerySet as TortoiseQuerySet
from tortoise.queryset import UpdateQuery as TortoiseUpdateQuery

from dipdup import fields
from dipdup.exceptions import FrameworkException
from dipdup.performance import caches
from dipdup.utils import json_dumps_plain

if TYPE_CHECKING:
    from collections import deque
    from collections.abc import Iterable

    from tortoise.backends.base.client import BaseDBAsyncClient
    from tortoise.expressions import Q

_logger = logging.getLogger(__name__)


# NOTE: Skip expensive copy() calls on each queryset update. Doesn't affect us. Definitely will be in Kleinmann officially.
tortoise.queryset.QuerySet._clone = lambda self: self  # type: ignore[method-assign]


class IndexType(Enum):
    """Enum for `dipdup.models.Index`"""

    tezos_tzkt_operations = 'tezos.tzkt.operations'
    tezos_tzkt_operations_unfiltered = 'tezos.tzkt.operations_unfiltered'
    tezos_tzkt_big_maps = 'tezos.tzkt.big_maps'
    tezos_tzkt_head = 'tezos.tzkt.head'
    tezos_tzkt_token_transfers = 'tezos.tzkt.token_transfers'
    tezos_tzkt_token_balances = 'tezos.tzkt.token_balances'
    tezos_tzkt_events = 'tezos.tzkt.events'
    evm_subsquid_events = 'evm.subsquid.events'


class MessageType:
    value: str


class IndexStatus(Enum):
    new = 'new'
    syncing = 'syncing'
    realtime = 'realtime'
    disabled = 'disabled'
    failed = 'failed'


# NOTE: Used as a key in config, must inherit from str
class ReindexingReason(str, Enum):
    """Reason that caused reindexing"""

    manual = 'manual'
    migration = 'migration'
    rollback = 'rollback'
    config_modified = 'config_modified'
    schema_modified = 'schema_modified'


class ReindexingAction(Enum):
    """Action that should be performed on reindexing"""

    exception = 'exception'
    wipe = 'wipe'
    ignore = 'ignore'


class SkipHistory(Enum):
    """Whether to skip indexing operation history and use only current state"""

    never = 'never'
    once = 'once'
    always = 'always'


@dataclass
class VersionedTransaction:
    """Metadata of currently opened versioned transaction."""

    level: int
    index: str
    immune_tables: set[str]


# NOTE: Overwritten by TransactionManager.register()
def get_transaction() -> VersionedTransaction | None:
    """Get metadata of currently opened versioned transaction if any"""
    raise FrameworkException('TransactionManager is not registered')


# NOTE: Overwritten by TransactionManager.register()
def get_pending_updates() -> deque[ModelUpdate]:
    """Get pending model updates queue"""
    raise FrameworkException('TransactionManager is not registered')


class ModelUpdateAction(Enum):
    """Mapping for actions in model update"""

    INSERT = 'INSERT'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'


class ModelUpdate(TortoiseModel):
    """Model update created within versioned transactions"""

    model_name = fields.TextField()
    model_pk = fields.TextField()
    level = fields.IntField()
    index = fields.TextField()

    action = fields.EnumField(ModelUpdateAction)
    data: dict[str, Any] = fields.JSONField(encoder=json_dumps_plain, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_model_update'

    @classmethod
    def from_model(cls, model: Model, action: ModelUpdateAction) -> ModelUpdate | None:
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
            'ModelUpdate saved: %s(%s) %s',
            self.model_name,
            self.model_pk,
            self.action.value,
        )
        return self

    async def revert(self, model: type[TortoiseModel]) -> None:
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

                # NOTE: There are possibly more non-JSON-deserializable fields.

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
        model: type[TortoiseModel],
        update_kwargs: dict[str, Any],
        db: BaseDBAsyncClient,
        q_objects: list[Q],
        annotations: dict[str, Any],
        custom_filters: dict[str, dict[str, Any]],
        limit: int | None,
        orderings: list[tuple[str, str]],
        filter_queryset: TortoiseQuerySet,  # type: ignore[type-arg]
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
            for key, value in self.update_kwargs.items():
                setattr(model, key, value)

            if update := ModelUpdate.from_model(model, ModelUpdateAction.UPDATE):
                get_pending_updates().append(update)

        return await super()._execute()


class DeleteQuery(TortoiseDeleteQuery):
    def __init__(
        self,
        model: type[TortoiseModel],
        db: BaseDBAsyncClient,
        q_objects: list[Q],
        annotations: dict[str, Any],
        custom_filters: dict[str, dict[str, Any]],
        limit: int | None,
        orderings: list[tuple[str, str]],
        filter_queryset: TortoiseQuerySet,  # type: ignore[type-arg]
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
    async def _execute(self) -> list[MODEL]:
        for model in self.objects:
            if update := ModelUpdate.from_model(
                cast(Model, model),
                ModelUpdateAction.INSERT,
            ):
                get_pending_updates().append(update)

        # NOTE: A bug; raises "You should first call .save()..." otherwise
        models: list[MODEL] = await super()._execute()
        for model in models:
            model._saved_in_db = True
        return models


class QuerySet(TortoiseQuerySet):  # type: ignore[type-arg]
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


# NOTE: Don't register cache; plain dict is faster
_versioned_fields: dict[type[Model], frozenset[str]] = {}


def get_versioned_fields(model: type[Model]) -> frozenset[str]:
    if model in _versioned_fields:
        return _versioned_fields[model]

    field_names: set[str] = set()
    field_keys = model._meta.db_fields.union(model._meta.fk_fields)

    for key, field_ in model._meta.fields_map.items():
        if key not in field_keys:
            continue
        if field_.pk:
            continue
        if isinstance(field_, relational.ForeignKeyFieldInstance):
            field_names.add(f'{key}_id')
        else:
            field_names.add(key)

    _versioned_fields[model] = frozenset(field_names)
    return frozenset(field_names)


class Model(TortoiseModel):
    """Base class for DipDup project models"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._original_versioned_data = self.versioned_data

    @classmethod
    def _init_from_db(cls, **kwargs: Any) -> Model:
        model = super()._init_from_db(**kwargs)
        model._original_versioned_data = model.versioned_data
        return model

    @property
    def original_versioned_data(self) -> dict[str, Any]:
        """Get versioned data of the model at the time of creation"""
        return self._original_versioned_data

    @property
    def versioned_data(self) -> dict[str, Any]:
        """Get versioned data of the model at the current time"""
        return {name: getattr(self, name) for name in get_versioned_fields(self.__class__)}

    @property
    def versioned_data_diff(self) -> dict[str, Any]:
        """Get versioned data of the model changed since creation"""
        data = {}
        for key, value in self.original_versioned_data.items():
            if value != self.versioned_data[key]:
                data[key] = value
        return data

    # NOTE: Do not touch docstrings below this line to preserve Tortoise ones
    async def delete(
        self,
        using_db: BaseDBAsyncClient | None = None,
    ) -> None:
        await super().delete(using_db=using_db)

        if update := ModelUpdate.from_model(self, ModelUpdateAction.DELETE):
            get_pending_updates().append(update)

    async def save(
        self,
        using_db: BaseDBAsyncClient | None = None,
        update_fields: Iterable[str] | None = None,
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
    def filter(cls, *args: Any, **kwargs: Any) -> TortoiseQuerySet:  # type: ignore[type-arg]
        return QuerySet(cls).filter(*args, **kwargs)

    @classmethod
    async def create(
        cls: type[ModelT],
        using_db: BaseDBAsyncClient | None = None,
        **kwargs: Any,
    ) -> ModelT:
        instance = cls(**kwargs)
        instance._saved_in_db = False
        db = using_db or cls._choose_db(True)
        await instance.save(using_db=db, force_create=True)
        return instance

    @classmethod
    def bulk_create(
        cls: type[Model],
        objects: Iterable[Model],
        batch_size: int | None = None,
        ignore_conflicts: bool = False,
        update_fields: Iterable[str] | None = None,
        on_conflict: Iterable[str] | None = None,
        using_db: BaseDBAsyncClient | None = None,
    ) -> BulkCreateQuery:
        if ignore_conflicts and update_fields:
            raise ValueError(
                'ignore_conflicts and update_fields are mutually exclusive.',
            )
        if not ignore_conflicts:
            if (update_fields and not on_conflict) or (on_conflict and not update_fields):
                raise ValueError('update_fields and on_conflict need set in same time.')

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
        cls: type[Model],
        objects: Iterable[Model],
        fields: Iterable[str],
        batch_size: int | None = None,
        using_db: BaseDBAsyncClient | None = None,
    ) -> BulkUpdateQuery:
        if any(obj.pk is None for obj in objects):
            raise ValueError('All bulk_update() objects must have a primary key set.')

        self = QuerySet(cls)
        return BulkUpdateQuery(
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


class CachedModel(Model):
    @classmethod
    async def preload(cls) -> None:
        _logger.info('Loading `%s` into memory', cls.__name__)
        query = cls.all()
        with suppress(AttributeError):
            query = query.limit(cls.Meta.maxsize)  # type: ignore[attr-defined]

        # NOTE: Table can be missing
        with suppress(OperationalError):
            async for model in query:
                model.cache()

    @classmethod
    async def cached_get(
        cls: type[ModelT],
        pk: int | str,
    ) -> ModelT:
        cls_cache = caches._model[cls.__name__]

        if pk not in cls_cache:
            cls_cache[pk] = await cls.get(pk=pk)
        return cls_cache[pk]  # type: ignore[return-value]

    @classmethod
    async def cached_get_or_none(
        cls: type[ModelT],
        pk: int | str,
    ) -> ModelT | None:
        cls_cache = caches._model[cls.__name__]

        if pk not in cls_cache:
            cls_cache[pk] = await cls.get_or_none(pk=pk)  # type: ignore[assignment]
        return cls_cache[pk]  # type: ignore[return-value]

    def cache(self) -> None:
        cls_cache = caches._model[self.__class__.__name__]
        if self.pk is None:
            raise FrameworkException('Cannot cache model without PK')
        if self.pk in cls_cache:
            raise FrameworkException(f'Model {self} is already cached')
        cls_cache[self.pk] = self

    class Meta:
        abstract = True


ModelT = TypeVar('ModelT', bound=Model)


# ===> Built-in Models (not versioned)


class Schema(TortoiseModel):
    name = fields.TextField(pk=True)
    hash = fields.TextField(null=True)
    reindex = fields.EnumField(ReindexingReason, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_schema'


class Head(TortoiseModel):
    name = fields.TextField(pk=True)
    level = fields.IntField()
    hash = fields.TextField(null=True)
    timestamp = fields.DatetimeField()

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_head'


class Index(TortoiseModel):
    name = fields.TextField(pk=True)
    type = fields.EnumField(IndexType)
    status = fields.EnumField(IndexStatus, default=IndexStatus.new)

    config_hash = fields.TextField(null=True)
    template = fields.TextField(null=True)
    template_values: dict[str, Any] = fields.JSONField(encoder=json_dumps_plain, null=True)

    level = fields.IntField(default=0)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_index'


class ContractKind(Enum):
    """Mapping for contract kind in"""

    TEZOS = 'tezos'
    EVM = 'evm'


class Contract(TortoiseModel):
    name = fields.TextField(pk=True)
    address = fields.TextField(null=True)
    code_hash = fields.BigIntField(null=True)
    typename = fields.TextField(null=True)
    kind = fields.EnumField(ContractKind)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_contract'


class Meta(TortoiseModel):
    key = fields.TextField(pk=True)
    value = fields.JSONField(encoder=json_dumps_plain, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_meta'


# ===> Built-in Models (versioned)


class ContractMetadata(Model):
    network = fields.TextField()
    contract = fields.TextField()
    metadata = fields.JSONField(encoder=json_dumps_plain, null=True)
    update_id = fields.IntField()

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_contract_metadata'
        unique_together = ('network', 'contract')


class TokenMetadata(Model):
    network = fields.TextField()
    contract = fields.TextField()
    token_id = fields.TextField()
    metadata = fields.JSONField(encoder=json_dumps_plain, null=True)
    update_id = fields.IntField()

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_token_metadata'
        unique_together = ('network', 'contract', 'token_id')
