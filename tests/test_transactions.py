"""Unit tests for TransactionManager.in_transaction error handling (see #1332)."""

from types import TracebackType
from typing import Any

import pytest

from dipdup import transactions as transactions_module
from dipdup.transactions import TransactionManager


class FakeTransactionContext:
    """Mimics tortoise's TransactionContext, including the rollback-masking behavior from #1332."""

    def __init__(
        self,
        on_error_exc: BaseException | None = None,
        on_success_exc: BaseException | None = None,
    ) -> None:
        self._on_error_exc = on_error_exc
        self._on_success_exc = on_success_exc

    async def __aenter__(self) -> Any:
        return object()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            if self._on_error_exc is not None:
                # NOTE: Like tortoise's rollback(), this secondary failure replaces
                # NOTE: the original error, chained as __context__.
                raise self._on_error_exc
        elif self._on_success_exc is not None:
            raise self._on_success_exc


def _patch(monkeypatch: pytest.MonkeyPatch, ctx: FakeTransactionContext) -> None:
    monkeypatch.setattr(transactions_module, 'in_transaction', lambda: ctx)
    monkeypatch.setattr(transactions_module, 'get_connection', lambda: object())
    monkeypatch.setattr(transactions_module, 'set_connection', lambda conn: None)


async def test_failed_rollback_does_not_mask_original_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """The connection-loss error must surface, not the rollback failure (see #1332)."""
    original = ConnectionError('cannot call Connection.fetch(): connection has been released back to the pool')
    rollback_failure = ConnectionError('cannot call Transaction.rollback(): the underlying connection is closed')
    _patch(monkeypatch, FakeTransactionContext(on_error_exc=rollback_failure))

    manager = TransactionManager()
    with pytest.raises(ConnectionError) as exc_info:

        async def _body() -> None:
            async with manager.in_transaction():
                raise original

        await _body()

    assert exc_info.value is original
    assert exc_info.value.__suppress_context__


async def test_successful_rollback_preserves_original_error(monkeypatch: pytest.MonkeyPatch) -> None:
    original = RuntimeError('handler exploded')
    _patch(monkeypatch, FakeTransactionContext())

    manager = TransactionManager()
    with pytest.raises(RuntimeError) as exc_info:

        async def _body() -> None:
            async with manager.in_transaction():
                raise original

        await _body()

    assert exc_info.value is original


async def test_body_error_with_explicit_context_is_not_swapped(monkeypatch: pytest.MonkeyPatch) -> None:
    """A body exception chained with `raise ... from ...` must propagate itself, not its cause."""
    cause = ValueError('root cause')
    original = RuntimeError('handler exploded')
    _patch(monkeypatch, FakeTransactionContext())

    manager = TransactionManager()
    with pytest.raises(RuntimeError) as exc_info:

        async def _body() -> None:
            async with manager.in_transaction():
                raise original from cause

        await _body()

    assert exc_info.value is original


async def test_failed_commit_without_body_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    commit_failure = ConnectionError('cannot call Transaction.commit(): the underlying connection is closed')
    _patch(monkeypatch, FakeTransactionContext(on_success_exc=commit_failure))

    manager = TransactionManager()
    with pytest.raises(ConnectionError) as exc_info:

        async def _body() -> None:
            async with manager.in_transaction():
                pass

        await _body()

    assert exc_info.value is commit_failure


async def test_clean_body_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, FakeTransactionContext())

    manager = TransactionManager()

    async def _body() -> None:
        async with manager.in_transaction():
            pass

    await _body()
