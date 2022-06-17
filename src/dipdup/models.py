from dataclasses import field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from typing import Dict
from typing import Generic
from typing import Iterable
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Type
from typing import TypeVar

from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from tortoise import BaseDBAsyncClient
from tortoise import ForeignKeyFieldInstance
from tortoise import Model as TortoiseModel
from tortoise import fields

from dipdup.enums import IndexStatus
from dipdup.enums import IndexType
from dipdup.enums import ReindexingReason
from dipdup.enums import TokenStandard
from dipdup.utils import json_dumps

ParameterType = TypeVar('ParameterType', bound=BaseModel)
StorageType = TypeVar('StorageType', bound=BaseModel)
KeyType = TypeVar('KeyType', bound=BaseModel)
ValueType = TypeVar('ValueType', bound=BaseModel)


# ===> Dataclasses


@dataclass
class OperationData:
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
    active: bool
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


@dataclass
class TokenTransferData:
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


@dataclass
class DatabaseTransaction:
    level: int
    index: str
    immune_tables: Set[str]


# NOTE: Overwritten by TransactionManager.register()
def get_transaction() -> Optional[DatabaseTransaction]:
    raise RuntimeError('TransactionManager is not registered')


class ModelUpdateAction(Enum):
    INSERT = 'INSERT'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'


class ModelUpdate(TortoiseModel):
    table_name = fields.CharField(256)
    table_pk = fields.CharField(256)
    level = fields.IntField()
    index = fields.CharField(256)

    action = fields.CharEnumField(ModelUpdateAction)
    data = fields.JSONField(encoder=json_dumps, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'dipdup_model_update'


class Model(TortoiseModel):
    @property
    def _update_data(self) -> Dict[str, Any]:
        update_data = {}
        for key, field_ in self._meta.fields_map.items():
            if field_.pk:
                continue
            if isinstance(field_, ForeignKeyFieldInstance):
                continue
            value = getattr(self, key)
            if isinstance(value, fields.ReverseRelation):
                continue
            update_data[key] = getattr(self, key)

        return update_data

    async def delete(
        self,
        using_db: Optional[BaseDBAsyncClient] = None,
    ) -> None:
        await super().delete(using_db=using_db)

        if not (transaction := get_transaction()):
            return
        if self._meta.db_table in transaction.immune_tables:
            return

        await ModelUpdate.create(
            table_name=self._meta.db_table,
            table_pk=self.pk,
            level=transaction.level,
            index=transaction.index,
            action=ModelUpdateAction.DELETE,
            data=self._update_data,
        )

    async def save(
        self,
        using_db: Optional[BaseDBAsyncClient] = None,
        update_fields: Optional[Iterable[str]] = None,
        force_create: bool = False,
        force_update: bool = False,
    ) -> None:
        saved_in_db = self._saved_in_db
        await super().save(
            using_db=using_db,
            update_fields=update_fields,
            force_create=force_create,
            force_update=force_update,
        )

        if not (transaction := get_transaction()):
            return
        if self._meta.db_table in transaction.immune_tables:
            return

        if not saved_in_db:
            await ModelUpdate.create(
                table_name=self._meta.db_table,
                table_pk=self.pk,
                level=transaction.level,
                index=transaction.index,
                action=ModelUpdateAction.INSERT,
                data=None,
            )
        else:
            await ModelUpdate.create(
                table_name=self._meta.db_table,
                table_pk=self.pk,
                level=transaction.level,
                index=transaction.index,
                action=ModelUpdateAction.UPDATE,
                data=self._update_data,
            )

    @classmethod
    async def create(
        cls: Type['Model'],
        using_db: Optional[BaseDBAsyncClient] = None,
        **kwargs: Any,
    ) -> 'Model':
        instance = cls(**kwargs)
        instance._saved_in_db = False
        db = using_db or cls._choose_db(True)
        await instance.save(using_db=db, force_create=True)
        return instance

    class Meta:
        abstract = True


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
