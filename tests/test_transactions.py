import asyncio
from collections.abc import AsyncIterator
from datetime import UTC
from datetime import datetime

import pytest
from tortoise import Tortoise
from tortoise.backends.sqlite.client import SqliteTransactionWrapper

from dipdup.database import get_connection
from dipdup.database import tortoise_wrapper
from dipdup.models import Head
from dipdup.transactions import TransactionManager

TIMEOUT = 10


class ConnectionLost(Exception): ...


class BodyFailed(Exception): ...


async def _connection_lost(self: SqliteTransactionWrapper) -> None:
    raise ConnectionLost('cannot call Transaction.rollback(): the underlying connection is closed')


@pytest.fixture
async def transactions() -> AsyncIterator[TransactionManager]:
    async with tortoise_wrapper('sqlite://:memory:'):
        async with asyncio.timeout(TIMEOUT):
            await Tortoise.generate_schemas()
        yield TransactionManager()


async def test_rollback_failure_keeps_original_error(
    transactions: TransactionManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(SqliteTransactionWrapper, 'rollback', _connection_lost)

    async with asyncio.timeout(TIMEOUT):
        with pytest.raises(BodyFailed) as exc_info:
            async with transactions.in_transaction():
                raise BodyFailed('connection has been released back to the pool')

    exc = exc_info.value
    assert isinstance(exc.__context__, ConnectionLost)
    assert any('ConnectionLost' in note for note in exc.__notes__)


async def test_commit_failure_propagates(
    transactions: TransactionManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(SqliteTransactionWrapper, 'commit', _connection_lost)

    async with asyncio.timeout(TIMEOUT):
        with pytest.raises(ConnectionLost):
            async with transactions.in_transaction():
                pass


async def test_cancellation_propagates(transactions: TransactionManager) -> None:
    async with asyncio.timeout(TIMEOUT):
        with pytest.raises(asyncio.CancelledError):
            async with transactions.in_transaction():
                raise asyncio.CancelledError


async def test_body_error_propagates_unchanged(transactions: TransactionManager) -> None:
    async with asyncio.timeout(TIMEOUT):
        with pytest.raises(BodyFailed) as exc_info:
            async with transactions.in_transaction():
                raise BodyFailed

    assert exc_info.value.__context__ is None
    assert not hasattr(exc_info.value, '__notes__')


async def test_success_commits_and_restores_connection(transactions: TransactionManager) -> None:
    original_conn = get_connection()

    async with asyncio.timeout(TIMEOUT):
        async with transactions.in_transaction():
            assert get_connection() is not original_conn
            await Head(name='test', level=1, hash='hash', timestamp=datetime.now(UTC)).save()

    assert get_connection() is original_conn
    assert await Head.filter(name='test').count() == 1
