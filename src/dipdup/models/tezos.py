from datetime import UTC
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from typing import Generic
from typing import TypeVar

from pydantic import BaseModel
from pydantic import Field
from pydantic.dataclasses import dataclass

from dipdup.fetcher import HasLevel

DEFAULT_ENTRYPOINT = 'default'

ParameterType = TypeVar('ParameterType', bound=BaseModel)
StorageType = TypeVar('StorageType', bound=BaseModel)
KeyType = TypeVar('KeyType', bound=BaseModel)
ValueType = TypeVar('ValueType', bound=BaseModel)
EventType = TypeVar('EventType', bound=BaseModel)


def _parse_timestamp(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp[:-1]).replace(tzinfo=UTC)


class TezosTokenStandard(Enum):
    FA12 = 'fa1.2'
    FA2 = 'fa2'


class TezosOperationType(Enum):
    """Type of blockchain operation

    :param transaction: transaction
    :param origination: origination
    :param migration: migration
    :param sr_execute: sr_execute
    :param sr_cement: sr_cement
    """

    transaction = 'transaction'
    origination = 'origination'
    migration = 'migration'
    sr_execute = 'sr_execute'
    sr_cement = 'sr_cement'


@dataclass(frozen=True)
class TezosOperationData(HasLevel):
    """Basic structure for operations from TzKT response"""

    type: str
    id: int
    level: int
    timestamp: datetime
    hash: str
    counter: int
    sender_address: str | None
    target_address: str | None
    initiator_address: str | None
    amount: int | None
    status: str
    has_internals: bool | None
    storage: Any
    diffs: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    block: str | None = None
    sender_alias: str | None = None
    nonce: int | None = None
    target_alias: str | None = None
    initiator_alias: str | None = None
    entrypoint: str | None = None
    parameter_json: Any | None = None
    originated_contract_address: str | None = None
    originated_contract_alias: str | None = None
    originated_contract_type_hash: int | None = None
    originated_contract_code_hash: int | None = None
    originated_contract_tzips: tuple[str, ...] | None = None
    delegate_address: str | None = None
    delegate_alias: str | None = None
    target_code_hash: int | None = None
    sender_code_hash: int | None = None
    commitment_json: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_json(
        cls,
        operation_json: dict[str, Any],
        type_: str | None = None,
    ) -> 'TezosOperationData':
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

        commitment_json = operation_json.get('commitment') or {}
        if operation_json['type'] in ['sr_execute', 'sr_cement']:
            target_json = operation_json.get('rollup') or {}
            initiator_json = commitment_json.get('initiator') or {}

        entrypoint, parameter = parameter_json.get('entrypoint'), parameter_json.get('value')
        if target_json.get('address', '').startswith('KT1'):
            # NOTE: TzKT returns None for `default` entrypoint
            if entrypoint is None:
                entrypoint = DEFAULT_ENTRYPOINT

                # NOTE: Empty parameter in this case means `{"prim": "Unit"}`
                if parameter is None:
                    parameter = {}

        return TezosOperationData(
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
            commitment_json=commitment_json,
        )

    @classmethod
    def from_migration_json(
        cls,
        migration_origination_json: dict[str, Any],
    ) -> 'TezosOperationData':
        """Convert raw migration message from REST into dataclass"""
        return TezosOperationData(
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
class TezosTransaction(Generic[ParameterType, StorageType]):
    """Wrapper for matched transaction with typed data passed to the handler"""

    data: TezosOperationData
    parameter: ParameterType
    storage: StorageType


@dataclass(frozen=True)
class TezosOrigination(Generic[StorageType]):
    """Wrapper for matched origination with typed data passed to the handler"""

    data: TezosOperationData
    storage: StorageType


@dataclass(frozen=True)
class TezosSmartRollupCommitment:
    id: int
    initiator_address: str
    initiator_alias: str | None
    inbox_level: int
    state: str
    hash: str | None
    ticks: int
    first_level: int
    first_time: datetime

    @classmethod
    def create(cls, operation_data: TezosOperationData) -> 'TezosSmartRollupCommitment':
        commitment_data = operation_data.commitment_json
        initiator_data = commitment_data.get('initiator') or {}
        return cls(
            id=commitment_data['id'],
            initiator_address=initiator_data['address'],
            initiator_alias=initiator_data.get('alias'),
            inbox_level=commitment_data['inboxLevel'],
            state=commitment_data['state'],
            hash=commitment_data.get('hash'),
            ticks=commitment_data['ticks'],
            first_level=commitment_data['firstLevel'],
            first_time=commitment_data['firstTime'],
        )


@dataclass(frozen=True)
class TezosSmartRollupExecute:
    """Wrapper for matched smart rollup execute to the handler"""

    data: TezosOperationData
    commitment: TezosSmartRollupCommitment

    @classmethod
    def create(cls, operation_data: TezosOperationData) -> 'TezosSmartRollupExecute':
        commitment = TezosSmartRollupCommitment.create(operation_data)
        return cls(
            data=operation_data,
            commitment=commitment,
        )


@dataclass(frozen=True)
class TezosSmartRollupCement:
    """Wrapper for matched smart rollup cement to the handler"""

    data: TezosOperationData
    commitment: TezosSmartRollupCommitment

    @classmethod
    def create(cls, operation_data: TezosOperationData) -> 'TezosSmartRollupCement':
        commitment = TezosSmartRollupCommitment.create(operation_data)
        return cls(
            data=operation_data,
            commitment=commitment,
        )


class TezosBigMapAction(Enum):
    """Mapping for action in TzKT response"""

    ALLOCATE = 'allocate'
    ADD_KEY = 'add_key'
    UPDATE_KEY = 'update_key'
    REMOVE_KEY = 'remove_key'
    REMOVE = 'remove'

    @property
    def has_key(self) -> bool:
        return self in (
            TezosBigMapAction.ADD_KEY,
            TezosBigMapAction.UPDATE_KEY,
            TezosBigMapAction.REMOVE_KEY,
        )

    @property
    def has_value(self) -> bool:
        return self in (TezosBigMapAction.ADD_KEY, TezosBigMapAction.UPDATE_KEY)


@dataclass(frozen=True)
class TezosBigMapData(HasLevel):
    """Basic structure for big map diffs from TzKT response"""

    id: int
    level: int
    operation_id: int
    timestamp: datetime
    bigmap: int
    contract_address: str
    path: str
    action: TezosBigMapAction
    active: bool
    key: Any | None = None
    value: Any | None = None

    @classmethod
    def from_json(
        cls,
        big_map_json: dict[str, Any],
    ) -> 'TezosBigMapData':
        """Convert raw big map diff message from WS/REST into dataclass"""
        action = TezosBigMapAction(big_map_json['action'])
        active = action not in (TezosBigMapAction.REMOVE, TezosBigMapAction.REMOVE_KEY)
        return TezosBigMapData(
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
class TezosBigMapDiff(Generic[KeyType, ValueType]):
    """Wrapper for matched big map diff with typed data passed to the handler"""

    action: TezosBigMapAction
    data: TezosBigMapData
    key: KeyType | None
    value: ValueType | None


@dataclass(frozen=True)
class TezosBlockData(HasLevel):
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
    priority: int | None = None
    baker_address: str | None = None
    baker_alias: str | None = None

    @classmethod
    def from_json(
        cls,
        block_json: dict[str, Any],
    ) -> 'TezosBlockData':
        """Convert raw block message from REST into dataclass"""
        return TezosBlockData(
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
class TezosHeadBlockData(HasLevel):
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
    ) -> 'TezosHeadBlockData':
        """Convert raw head block message from WS/REST into dataclass"""
        return TezosHeadBlockData(
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
class TezosQuoteData(HasLevel):
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
    def from_json(cls, quote_json: dict[str, Any]) -> 'TezosQuoteData':
        """Convert raw quote message from REST into dataclass"""
        return TezosQuoteData(
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
class TezosTokenTransferData(HasLevel):
    """Basic structure for token transver received from TzKT SignalR API"""

    id: int
    level: int
    timestamp: datetime
    tzkt_token_id: int
    contract_address: str | None = None
    contract_alias: str | None = None
    token_id: int | None = None
    standard: TezosTokenStandard | None = None
    metadata: dict[str, Any] | None = None
    from_alias: str | None = None
    from_address: str | None = None
    to_alias: str | None = None
    to_address: str | None = None
    amount: int | None = None
    tzkt_transaction_id: int | None = None
    tzkt_origination_id: int | None = None
    tzkt_migration_id: int | None = None

    @classmethod
    def from_json(cls, token_transfer_json: dict[str, Any]) -> 'TezosTokenTransferData':
        """Convert raw token transfer message from REST or WS into dataclass"""
        token_json = token_transfer_json.get('token') or {}
        contract_json = token_json.get('contract') or {}
        from_json = token_transfer_json.get('from') or {}
        to_json = token_transfer_json.get('to') or {}
        standard = token_json.get('standard')
        metadata = token_json.get('metadata')
        amount = token_transfer_json.get('amount')
        amount = int(amount) if amount is not None else None

        return TezosTokenTransferData(
            id=token_transfer_json['id'],
            level=token_transfer_json['level'],
            timestamp=_parse_timestamp(token_transfer_json['timestamp']),
            tzkt_token_id=token_json['id'],
            contract_address=contract_json.get('address'),
            contract_alias=contract_json.get('alias'),
            token_id=token_json.get('tokenId'),
            standard=TezosTokenStandard(standard) if standard else None,
            metadata=metadata if isinstance(metadata, dict) else {},
            from_alias=from_json.get('alias'),
            from_address=from_json.get('address'),
            to_alias=to_json.get('alias'),
            to_address=to_json.get('address'),
            amount=amount,
            tzkt_transaction_id=token_transfer_json.get('transactionId'),
            tzkt_origination_id=token_transfer_json.get('originationId'),
            tzkt_migration_id=token_transfer_json.get('migrationId'),
        )


@dataclass(frozen=True)
class TezosTokenBalanceData(HasLevel):
    """Basic structure for token transver received from TzKT SignalR API"""

    id: int
    transfers_count: int
    first_level: int
    first_time: datetime
    # NOTE: Level of the block where the token balance has been changed for the last time.
    last_level: int
    last_time: datetime
    account_address: str | None = None
    account_alias: str | None = None
    tzkt_token_id: int | None = None
    contract_address: str | None = None
    contract_alias: str | None = None
    token_id: int | None = None
    standard: TezosTokenStandard | None = None
    metadata: dict[str, Any] | None = None

    balance: str | None = None
    balance_value: float | None = None

    @property
    def level(self) -> int:  # type: ignore[override]
        return self.last_level

    @classmethod
    def from_json(cls, token_transfer_json: dict[str, Any]) -> 'TezosTokenBalanceData':
        """Convert raw token transfer message from REST or WS into dataclass"""
        token_json = token_transfer_json.get('token') or {}
        standard = token_json.get('standard')
        metadata = token_json.get('metadata')
        contract_json = token_json.get('contract') or {}

        return TezosTokenBalanceData(
            id=token_transfer_json['id'],
            transfers_count=token_transfer_json['transfersCount'],
            first_level=token_transfer_json['firstLevel'],
            first_time=_parse_timestamp(token_transfer_json['firstTime']),
            last_level=token_transfer_json['lastLevel'],
            last_time=_parse_timestamp(token_transfer_json['lastTime']),
            account_address=token_transfer_json.get('account', {}).get('address'),
            account_alias=token_transfer_json.get('account', {}).get('alias'),
            tzkt_token_id=token_json['id'],
            contract_address=contract_json.get('address'),
            contract_alias=contract_json.get('alias'),
            token_id=token_json.get('tokenId'),
            standard=TezosTokenStandard(standard) if standard else None,
            metadata=metadata if isinstance(metadata, dict) else {},
            balance=token_transfer_json.get('balance'),
            balance_value=token_transfer_json.get('balanceValue'),
        )


@dataclass(frozen=True)
class TezosEventData(HasLevel):
    """Basic structure for events received from TzKT REST API"""

    id: int
    level: int
    timestamp: datetime
    tag: str
    payload: Any | None
    contract_address: str
    contract_alias: str | None = None
    contract_code_hash: int | None = None
    transaction_id: int | None = None

    @classmethod
    def from_json(cls, event_json: dict[str, Any]) -> 'TezosEventData':
        """Convert raw event message from WS/REST into dataclass"""
        return TezosEventData(
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
class TezosEvent(Generic[EventType]):
    data: TezosEventData
    payload: EventType


@dataclass(frozen=True)
class TezosUnknownEvent:
    data: TezosEventData
    payload: Any | None
