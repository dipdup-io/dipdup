import asyncio

from aiosignalrcore.transport.websockets.reconnection import ConnectionStateChecker  # type: ignore

__version__ = '0.1.0'


async def run(self):
    while self.running:
        await asyncio.sleep(self.keep_alive_interval)
        await self.ping_function()


# FIXME: https://github.com/mandrewcito/signalrcore/pull/58
ConnectionStateChecker.run = run
