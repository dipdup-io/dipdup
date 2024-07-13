from abc import abstractmethod
from enum import Enum
from typing import Any
from typing import Literal

from pydantic import Field
from pydantic.dataclasses import dataclass

from dipdup.exceptions import FrameworkException
from dipdup.models import MessageType
from dipdup.subscriptions import Subscription


class TezosTzktMessageType(MessageType, Enum):
    """Enum for realtime message types"""

    operation = 'operation'
    big_map = 'big_map'
    head = 'head'
    token_transfer = 'token_transfer'
    token_balance = 'token_balance'
    event = 'event'


class TezosTzktSubscription(Subscription):
    type: str
    method: str

    @abstractmethod
    def get_request(self) -> Any: ...


@dataclass(frozen=True)
class HeadSubscription(TezosTzktSubscription):
    type: Literal['head'] = 'head'
    method: Literal['SubscribeToHead'] = 'SubscribeToHead'

    def get_request(self) -> list[dict[str, str]]:
        return []


@dataclass(frozen=True)
class OriginationSubscription(TezosTzktSubscription):
    type: Literal['origination'] = 'origination'
    method: Literal['SubscribeToOperations'] = 'SubscribeToOperations'

    def get_request(self) -> list[dict[str, Any]]:
        return [{'types': 'origination'}]


@dataclass(frozen=True)
class TransactionSubscription(TezosTzktSubscription):
    type: Literal['transaction'] = 'transaction'
    method: Literal['SubscribeToOperations'] = 'SubscribeToOperations'
    address: str | None = None

    def get_request(self) -> list[dict[str, Any]]:
        request: dict[str, Any] = {'types': 'transaction'}
        if self.address:
            request['address'] = self.address
        return [request]


@dataclass(frozen=True)
class SmartRollupExecuteSubscription(TezosTzktSubscription):
    type: Literal['sr_execute'] = 'sr_execute'
    method: Literal['SubscribeToOperations'] = 'SubscribeToOperations'
    address: str | None = None

    def get_request(self) -> list[dict[str, Any]]:
        request: dict[str, Any] = {'types': 'sr_execute'}
        if self.address:
            request['address'] = self.address
        return [request]


@dataclass(frozen=True)
class SmartRollupCementSubscription(TezosTzktSubscription):
    type: Literal['sr_cement'] = 'sr_cement'
    method: Literal['SubscribeToOperations'] = 'SubscribeToOperations'
    address: str | None = None

    def get_request(self) -> list[dict[str, Any]]:
        request: dict[str, Any] = {'types': 'sr_cement'}
        if self.address:
            request['address'] = self.address
        return [request]


# TODO: Add `ptr` and `tags` filters?
@dataclass(frozen=True)
class BigMapSubscription(TezosTzktSubscription):
    type: Literal['big_map'] = 'big_map'
    method: Literal['SubscribeToBigMaps'] = 'SubscribeToBigMaps'
    address: str | None = None
    path: str | None = None

    def get_request(self) -> list[dict[str, Any]]:
        if self.address and self.path:
            return [{'address': self.address, 'paths': [self.path]}]
        if not self.address and not self.path:
            return [{}]
        raise FrameworkException('Either both `address` and `path` should be set or none of them')


@dataclass(frozen=True)
class TokenTransferSubscription(TezosTzktSubscription):
    type: Literal['token_transfer'] = 'token_transfer'
    method: Literal['SubscribeToTokenTransfers'] = 'SubscribeToTokenTransfers'
    contract: str | None = None
    token_id: int | None = None
    from_: str | None = Field(None)  # type: ignore[misc]
    to: str | None = None

    def get_request(self) -> list[dict[str, Any]]:
        request: dict[str, Any] = {}
        if self.token_id:
            request['tokenId'] = self.token_id
        if self.contract:
            request['contract'] = self.contract
        if self.from_:
            request['from'] = self.from_
        if self.to:
            request['to'] = self.to
        return [request]


@dataclass(frozen=True)
class TokenBalanceSubscription(TezosTzktSubscription):
    type: Literal['token_balance'] = 'token_balance'
    method: Literal['SubscribeToTokenBalances'] = 'SubscribeToTokenBalances'
    contract: str | None = None
    token_id: int | None = None

    def get_request(self) -> list[dict[str, Any]]:
        request: dict[str, Any] = {}
        if self.token_id:
            request['tokenId'] = self.token_id
        if self.contract:
            request['contract'] = self.contract
        return [request]


@dataclass(frozen=True)
class EventSubscription(TezosTzktSubscription):
    type: Literal['event'] = 'event'
    method: Literal['SubscribeToEvents'] = 'SubscribeToEvents'
    address: str | None = None

    def get_request(self) -> list[dict[str, Any]]:
        if self.address:
            return [{'address': self.address}]

        return [{}]
