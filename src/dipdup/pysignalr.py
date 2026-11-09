"""
Compatibility aliases for the `pysignalr` package.
"""

import asyncio
from typing import Any

import pysignalr.client
import pysignalr.transport.websocket
from pysignalr.messages import JSONMessage as WebsocketMessage
from pysignalr.messages import Message as Message
from pysignalr.protocol.json import BaseJSONProtocol as WebsocketProtocol
from pysignalr.transport.abstract import ConnectionState
from websockets.asyncio.client import connect

__all__ = ['Message', 'SignalRClient', 'WebsocketMessage', 'WebsocketProtocol', 'WebsocketTransport']


class _SingleConnection(pysignalr.transport.websocket.WebsocketTransport):
    """Transport that makes a single connection: `run` raises once it fails or is lost"""

    # NOTE: The parent reconnects inside `run` and doesn't report a lost connection; `_ws_loop` reconnects instead
    async def run(self) -> None:
        await self._set_state(ConnectionState.connecting)
        if not self._skip_negotiation:
            await self._negotiate()

        ssl: dict[str, Any] = {} if self._ssl is None else {'ssl': self._ssl}
        conn = await connect(
            self._url,
            additional_headers=self._headers,
            ping_interval=self._ping_interval,
            open_timeout=self._connection_timeout,
            max_size=self._max_size,
            **ssl,
        )
        keepalive = asyncio.ensure_future(self._keepalive(conn))
        try:
            await self._handshake(conn)
            self._ws = conn
            await self._set_state(ConnectionState.connected)
            await asyncio.gather(self._process(conn), keepalive)
        finally:
            self._ws = None
            self._connected.clear()
            keepalive.cancel()
            # NOTE: Don't wait for a closing handshake that a dead server never sends
            conn.transport.abort()


class WebsocketTransport(_SingleConnection, pysignalr.transport.websocket.BaseWebsocketTransport):
    """Plain websocket transport without SignalR negotiation, handshake and pings"""


class SignalRClient(pysignalr.client.SignalRClient):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # NOTE: Same transport, but `run` makes a single connection
        self._transport.__class__ = _SingleConnection
