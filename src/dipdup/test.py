import asyncio
from contextlib import AsyncExitStack
from typing import Any

from dipdup.config import DipDupConfig
from dipdup.dipdup import DipDup
from dipdup.index import Index


async def create_dummy_dipdup(
    config: DipDupConfig,
    stack: AsyncExitStack,
) -> 'DipDup':
    """Create a dummy DipDup instance for testing purposes.

    Only basic initialization is performed:

    - Create datasources without spawning them
    - Register system hooks
    - Initialize Tortoise ORM and create schema

    You need to enter `AsyncExitStack` context manager prior to calling this method.
    """
    config.initialize()

    dipdup = DipDup(config)
    await dipdup._create_datasources()
    await dipdup._set_up_database(stack)
    await dipdup._set_up_hooks(set())
    await dipdup._initialize_schema()
    await dipdup._set_up_transactions(stack)
    await dipdup._set_up_index_dispatcher(
        tasks=set(),
        spawn_datasources_event=asyncio.Event(),
        start_scheduler_event=asyncio.Event(),
        early_realtime=False,
        run=False,
        metrics=False,
    )

    return dipdup


async def spawn_index(dipdup: DipDup, name: str) -> Index[Any, Any, Any]:
    """Spawn index from config and add it to dispatcher."""
    dispatcher = dipdup._get_event_dispatcher()
    index: Index[Any, Any, Any] = await dispatcher._ctx._spawn_index(name)
    dispatcher._indexes[name] = dispatcher._ctx._pending_indexes.pop()
    return index
