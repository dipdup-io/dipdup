"""
Compatibility aliases for the `pysignalr` package.
"""

from typing import Any

from pysignalr.messages import JSONMessage as WebsocketMessage
from pysignalr.messages import Message as Message
from pysignalr.protocol.json import BaseJSONProtocol as WebsocketProtocol
from pysignalr.transport.abstract import ConnectionState
from pysignalr.transport.websocket import BaseWebsocketTransport
from websockets.asyncio.client import connect

__all__ = ['Message', 'WebsocketMessage', 'WebsocketProtocol', 'WebsocketTransport']


class WebsocketTransport(BaseWebsocketTransport):
    """Plain websocket transport that makes a single connection: `run` raises once it fails or is lost"""

    # NOTE: The parent reconnects inside `run` forever and never reports a lost connection; `_ws_loop` reconnects instead
    async def run(self) -> None:
        await self._set_state(ConnectionState.connecting)
        ssl: dict[str, Any] = {} if self._ssl is None else {'ssl': self._ssl}
        try:
            async with connect(
                self._url,
                additional_headers=self._headers,
                ping_interval=self._ping_interval,
                open_timeout=self._connection_timeout,
                max_size=self._max_size,
                **ssl,
            ) as conn:
                self._ws = conn
                await self._set_state(ConnectionState.connected)
                await self._process(conn)
        finally:
            self._ws = None
            self._connected.clear()
