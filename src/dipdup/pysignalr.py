"""
Turning pysignalr back into a basic websocket client usable for JSONRPC nodes, but with state management and reconnection logic.

Eventually this code will be moved to the upstream library.
"""

import asyncio
from collections.abc import Iterable
from typing import Any

import orjson
from pysignalr.messages import HandshakeRequestMessage
from pysignalr.messages import HandshakeResponseMessage
from pysignalr.messages import Message as Message
from pysignalr.messages import MessageType
from pysignalr.protocol.abstract import Protocol
from pysignalr.transport.websocket import WebsocketTransport as SignalRWebsocketTransport
from websockets.client import WebSocketClientProtocol

KEEPALIVE_INTERVAL = 5


class WebsocketMessage(Message, type_=MessageType.invocation):
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    def dump(self) -> dict[str, Any]:
        return self.data


class WebsocketTransport(SignalRWebsocketTransport):
    async def _keepalive(self, conn: WebSocketClientProtocol) -> None:
        while True:
            await conn.ensure_open()
            await asyncio.sleep(KEEPALIVE_INTERVAL)

    async def _handshake(self, conn: WebSocketClientProtocol) -> None:
        return


class WebsocketProtocol(Protocol):
    def __init__(self) -> None:
        pass

    def decode(self, raw_message: str | bytes) -> tuple[WebsocketMessage]:
        json_message = orjson.loads(raw_message)
        return (WebsocketMessage(data=json_message),)

    def encode(self, message: Message | HandshakeRequestMessage) -> str | bytes:
        return orjson.dumps(message.dump())

    def decode_handshake(self, raw_message: str | bytes) -> tuple[HandshakeResponseMessage, Iterable[Message]]:
        raise NotImplementedError
