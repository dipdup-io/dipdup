from abc import abstractmethod
from datetime import datetime
from datetime import timezone
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
from dipdup.fetcher import HasLevel
from dipdup.models import MessageType
from dipdup.subscriptions import Subscription

ParameterType = TypeVar('ParameterType', bound=BaseModel)
StorageType = TypeVar('StorageType', bound=BaseModel)
KeyType = TypeVar('KeyType', bound=BaseModel)
ValueType = TypeVar('ValueType', bound=BaseModel)
EventType = TypeVar('EventType', bound=BaseModel)


def _parse_timestamp(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp[:-1]).replace(tzinfo=timezone.utc)


class TzktTokenStandard(Enum):
    FA12 = 'fa1.2'
    FA2 = 'fa2'


class TzktOperationType(Enum):
    """Type of blockchain operation"""

    transaction = 'transaction'
    origination = 'origination'
    migration = 'migration'


class TzktMessageType(MessageType, Enum):
    """Enum for realtime message types"""

    operation = 'operation'
    big_map = 'big_map'
    head = 'head'
    token_transfer = 'token_transfer'
    event = 'event'


class TzktSubscription(Subscription):
    type: str
    method: str

    @abstractmethod
    def get_request(self) -> Any:
        ...


@dataclass(frozen=True)
class HeadSubscription(TzktSubscription):
    type: Literal['head'] = 'head'
    method: Literal['SubscribeToHead'] = 'SubscribeToHead'

    def get_request(self) -> list[dict[str, str]]:
        return []


@dataclass(frozen=True)
class OriginationSubscription(TzktSubscription):
    type: Literal['origination'] = 'origination'
    method: Literal['SubscribeToOperations'] = 'SubscribeToOperations'

    def get_request(self) -> list[dict[str, Any]]:
        return [{'types': 'origination'}]


@dataclass(frozen=True)
class TransactionSubscription(TzktSubscription):
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
class BigMapSubscription(TzktSubscription):
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
class TokenTransferSubscription(TzktSubscription):
    type: Literal['token_transfer'] = 'token_transfer'
    method: Literal['SubscribeToTokenTransfers'] = 'SubscribeToTokenTransfers'
    contract: str | None = None
    token_id: int | None = None
    from_: str | None = Field(None, alias='from')  # type: ignore[misc]
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
class EventSubscription(TzktSubscription):
    type: Literal['event'] = 'event'
    method: Literal['SubscribeToEvents'] = 'SubscribeToEvents'
    address: str | None = None

    def get_request(self) -> list[dict[str, Any]]:
        if self.address:
            return [{'address': self.address}]

        return [{}]


@dataclass(frozen=True)
class TzktOperationData(HasLevel):
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

    @classmethod
    def from_json(
        cls,
        operation_json: dict[str, Any],
        type_: str | None = None,
    ) -> 'TzktOperationData':
        """Convert raw operation message from WS/REST into dataclass"""
        # NOTE: Migration originations are handled in a separate method
        sender_json = operation_json.get('sender') or {}
        target_json = operation_json.get('target') or {}
        initiator_json = operation_json.get('initiator') or {}
        delegate_json = operation_json.get('delegate') or {}
        parameter_json = operation_json.get('parameter') or {}
        originated_contract_json = operation_json.get('originatedContract') or {}

        if (amount := operation_json.get('contractBalance')) is None:
            amount = operation_json.get('amount')

        entrypoint, parameter = parameter_json.get('entrypoint'), parameter_json.get('value')
        if target_json.get('address', '').startswith('KT1'):
            # NOTE: TzKT returns None for `default` entrypoint
            if entrypoint is None:
                entrypoint = 'default'

                # NOTE: Empty parameter in this case means `{"prim": "Unit"}`
                if parameter is None:
                    parameter = {}

        return TzktOperationData(
            type=type_ or operation_json['type'],
            id=operation_json['id'],
            level=operation_json['level'],
            timestamp=_parse_timestamp(operation_json['timestamp']),
            block=operation_json.get('block'),
            hash=operation_json['hash'],
            counter=operation_json['counter'],
            sender_address=sender_json.get('address'),
            sender_code_hash=operation_json.get('senderCodeHash'),
            target_address=target_json.get('address'),
            target_code_hash=operation_json.get('targetCodeHash'),
            initiator_address=initiator_json.get('address'),
            amount=amount,
            status=operation_json['status'],
            has_internals=operation_json.get('hasInternals'),
            sender_alias=operation_json['sender'].get('alias'),
            nonce=operation_json.get('nonce'),
            target_alias=target_json.get('alias'),
            initiator_alias=initiator_json.get('alias'),
            entrypoint=entrypoint,
            parameter_json=parameter,
            originated_contract_address=originated_contract_json.get('address'),
            originated_contract_alias=originated_contract_json.get('alias'),
            originated_contract_type_hash=originated_contract_json.get('typeHash'),
            originated_contract_code_hash=originated_contract_json.get('codeHash'),
            originated_contract_tzips=originated_contract_json.get('tzips'),
            storage=operation_json.get('storage'),
            diffs=operation_json.get('diffs') or (),
            delegate_address=delegate_json.get('address'),
            delegate_alias=delegate_json.get('alias'),
        )

    @classmethod
    def from_migration_json(
        cls,
        migration_origination_json: dict[str, Any],
    ) -> 'TzktOperationData':
        """Convert raw migration message from REST into dataclass"""
        return TzktOperationData(
            type='migration',
            id=migration_origination_json['id'],
            level=migration_origination_json['level'],
            timestamp=_parse_timestamp(migration_origination_json['timestamp']),
            block=migration_origination_json.get('block'),
            originated_contract_address=migration_origination_json['account']['address'],
            originated_contract_alias=migration_origination_json['account'].get('alias'),
            amount=migration_origination_json['balanceChange'],
            storage=migration_origination_json.get('storage'),
            diffs=migration_origination_json.get('diffs') or (),
            status='applied',
            has_internals=False,
            hash='[none]',
            counter=0,
            sender_address='[none]',
            sender_code_hash=None,
            target_address=None,
            target_code_hash=None,
            initiator_address=None,
        )


@dataclass(frozen=True)
class TzktTransaction(Generic[ParameterType, StorageType]):
    """Wrapper for matched transaction with typed data passed to the handler"""

    data: TzktOperationData
    parameter: ParameterType
    storage: StorageType


@dataclass(frozen=True)
class TzktOrigination(Generic[StorageType]):
    """Wrapper for matched origination with typed data passed to the handler"""

    data: TzktOperationData
    storage: StorageType


class TzktBigMapAction(Enum):
    """Mapping for action in TzKT response"""

    ALLOCATE = 'allocate'
    ADD_KEY = 'add_key'
    UPDATE_KEY = 'update_key'
    REMOVE_KEY = 'remove_key'
    REMOVE = 'remove'

    @property
    def has_key(self) -> bool:
        return self in (TzktBigMapAction.ADD_KEY, TzktBigMapAction.UPDATE_KEY, TzktBigMapAction.REMOVE_KEY)

    @property
    def has_value(self) -> bool:
        return self in (TzktBigMapAction.ADD_KEY, TzktBigMapAction.UPDATE_KEY)


@dataclass(frozen=True)
class TzktBigMapData(HasLevel):
    """Basic structure for big map diffs from TzKT response"""

    id: int
    level: int
    operation_id: int
    timestamp: datetime
    bigmap: int
    contract_address: str
    path: str
    action: TzktBigMapAction
    active: bool
    key: Optional[Any] = None
    value: Optional[Any] = None

    @classmethod
    def from_json(
        cls,
        big_map_json: dict[str, Any],
    ) -> 'TzktBigMapData':
        """Convert raw big map diff message from WS/REST into dataclass"""
        action = TzktBigMapAction(big_map_json['action'])
        active = action not in (TzktBigMapAction.REMOVE, TzktBigMapAction.REMOVE_KEY)
        return TzktBigMapData(
            id=big_map_json['id'],
            level=big_map_json['level'],
            # NOTE: missing `operation_id` field in API to identify operation
            operation_id=big_map_json['level'],
            timestamp=_parse_timestamp(big_map_json['timestamp']),
            bigmap=big_map_json['bigmap'],
            contract_address=big_map_json['contract']['address'],
            path=big_map_json['path'],
            action=action,
            active=active,
            key=big_map_json.get('content', {}).get('key'),
            value=big_map_json.get('content', {}).get('value'),
        )


@dataclass(frozen=True)
class TzktBigMapDiff(Generic[KeyType, ValueType]):
    """Wrapper for matched big map diff with typed data passed to the handler"""

    action: TzktBigMapAction
    data: TzktBigMapData
    key: Optional[KeyType]
    value: Optional[ValueType]


@dataclass(frozen=True)
class TzktBlockData(HasLevel):
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

    @classmethod
    def from_json(
        cls,
        block_json: dict[str, Any],
    ) -> 'TzktBlockData':
        """Convert raw block message from REST into dataclass"""
        return TzktBlockData(
            level=block_json['level'],
            hash=block_json['hash'],
            timestamp=_parse_timestamp(block_json['timestamp']),
            proto=block_json['proto'],
            priority=block_json.get('priority'),
            validations=block_json['validations'],
            deposit=block_json['deposit'],
            reward=block_json['reward'],
            fees=block_json['fees'],
            nonce_revealed=block_json['nonceRevealed'],
            baker_address=block_json.get('baker', {}).get('address'),
            baker_alias=block_json.get('baker', {}).get('alias'),
        )


@dataclass(frozen=True)
class TzktHeadBlockData(HasLevel):
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

    @classmethod
    def from_json(
        cls,
        head_block_json: dict[str, Any],
    ) -> 'TzktHeadBlockData':
        """Convert raw head block message from WS/REST into dataclass"""
        return TzktHeadBlockData(
            chain=head_block_json['chain'],
            chain_id=head_block_json['chainId'],
            cycle=head_block_json['cycle'],
            level=head_block_json['level'],
            hash=head_block_json['hash'],
            protocol=head_block_json['protocol'],
            next_protocol=head_block_json['nextProtocol'],
            timestamp=_parse_timestamp(head_block_json['timestamp']),
            voting_epoch=head_block_json['votingEpoch'],
            voting_period=head_block_json['votingPeriod'],
            known_level=head_block_json['knownLevel'],
            last_sync=head_block_json['lastSync'],
            synced=head_block_json['synced'],
            quote_level=head_block_json['quoteLevel'],
            quote_btc=Decimal(head_block_json['quoteBtc']),
            quote_eur=Decimal(head_block_json['quoteEur']),
            quote_usd=Decimal(head_block_json['quoteUsd']),
            quote_cny=Decimal(head_block_json['quoteCny']),
            quote_jpy=Decimal(head_block_json['quoteJpy']),
            quote_krw=Decimal(head_block_json['quoteKrw']),
            quote_eth=Decimal(head_block_json['quoteEth']),
            quote_gbp=Decimal(head_block_json['quoteGbp']),
        )


@dataclass(frozen=True)
class TzktQuoteData(HasLevel):
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

    @classmethod
    def from_json(cls, quote_json: dict[str, Any]) -> 'TzktQuoteData':
        """Convert raw quote message from REST into dataclass"""
        return TzktQuoteData(
            level=quote_json['level'],
            timestamp=_parse_timestamp(quote_json['timestamp']),
            btc=Decimal(quote_json['btc']),
            eur=Decimal(quote_json['eur']),
            usd=Decimal(quote_json['usd']),
            cny=Decimal(quote_json['cny']),
            jpy=Decimal(quote_json['jpy']),
            krw=Decimal(quote_json['krw']),
            eth=Decimal(quote_json['eth']),
            gbp=Decimal(quote_json['gbp']),
        )


@dataclass(frozen=True)
class TzktTokenTransferData(HasLevel):
    """Basic structure for token transver received from TzKT SignalR API"""

    id: int
    level: int
    timestamp: datetime
    tzkt_token_id: int
    contract_address: Optional[str] = None
    contract_alias: Optional[str] = None
    token_id: Optional[int] = None
    standard: Optional[TzktTokenStandard] = None
    metadata: Optional[dict[str, Any]] = None
    from_alias: Optional[str] = None
    from_address: Optional[str] = None
    to_alias: Optional[str] = None
    to_address: Optional[str] = None
    amount: Optional[int] = None
    tzkt_transaction_id: Optional[int] = None
    tzkt_origination_id: Optional[int] = None
    tzkt_migration_id: Optional[int] = None

    @classmethod
    def from_json(cls, token_transfer_json: dict[str, Any]) -> 'TzktTokenTransferData':
        """Convert raw token transfer message from REST or WS into dataclass"""
        token_json = token_transfer_json.get('token') or {}
        contract_json = token_json.get('contract') or {}
        from_json = token_transfer_json.get('from') or {}
        to_json = token_transfer_json.get('to') or {}
        standard = token_json.get('standard')
        metadata = token_json.get('metadata')
        return TzktTokenTransferData(
            id=token_transfer_json['id'],
            level=token_transfer_json['level'],
            timestamp=_parse_timestamp(token_transfer_json['timestamp']),
            tzkt_token_id=token_json['id'],
            contract_address=contract_json.get('address'),
            contract_alias=contract_json.get('alias'),
            token_id=token_json.get('tokenId'),
            standard=TzktTokenStandard(standard) if standard else None,
            metadata=metadata if isinstance(metadata, dict) else {},
            from_alias=from_json.get('alias'),
            from_address=from_json.get('address'),
            to_alias=to_json.get('alias'),
            to_address=to_json.get('address'),
            amount=token_transfer_json.get('amount'),
            tzkt_transaction_id=token_transfer_json.get('transactionId'),
            tzkt_origination_id=token_transfer_json.get('originationId'),
            tzkt_migration_id=token_transfer_json.get('migrationId'),
        )


@dataclass(frozen=True)
class TzktEventData(HasLevel):
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

    @classmethod
    def from_json(cls, event_json: dict[str, Any]) -> 'TzktEventData':
        """Convert raw event message from WS/REST into dataclass"""
        return TzktEventData(
            id=event_json['id'],
            level=event_json['level'],
            timestamp=_parse_timestamp(event_json['timestamp']),
            tag=event_json['tag'],
            payload=event_json.get('payload'),
            contract_address=event_json['contract']['address'],
            contract_alias=event_json['contract'].get('alias'),
            contract_code_hash=event_json['codeHash'],
            transaction_id=event_json.get('transactionId'),
        )


@dataclass(frozen=True)
class TzktEvent(Generic[EventType]):
    data: TzktEventData
    payload: EventType


@dataclass(frozen=True)
class TzktUnknownEvent:
    data: TzktEventData
    payload: Any | None
