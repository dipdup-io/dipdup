import atexit
import logging
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from typing import cast

import pytest

from dipdup import env
from dipdup import report
from dipdup.cli import _cli_wrapper
from dipdup.exceptions import DatasourceError
from dipdup.report import save_report
from dipdup.sentry import extract_event


def _run_wrapped(fn: Callable[..., Any], ctx: Any) -> None:
    # NOTE: Typed as the async command, but at runtime the wrapper is sync and drives the coroutine itself
    cast('Callable[[Any], None]', _cli_wrapper(fn))(ctx)


def _chained_error_with_tracebackless_cause() -> Exception:
    """Build an exception chain whose innermost cause was never raised, so it has no traceback."""
    try:
        try:
            # NOTE: Constructed, not raised - it has no __traceback__, so Sentry emits no `stacktrace`
            cause = ConnectionResetError(104, 'Connection reset by peer')
            raise ConnectionError('connection was closed in the middle of operation') from cause
        except ConnectionError as e:
            raise RuntimeError('cannot call Transaction.rollback()') from e
    except RuntimeError as e:
        return e


async def test_extract_event_has_tracebackless_value() -> None:
    # NOTE: Guards the precondition - the chain really does yield a value without `stacktrace`
    error = _chained_error_with_tracebackless_cause()
    values = extract_event(error)['exception']['values']
    assert any('stacktrace' not in value for value in values)


async def test_save_report_with_tracebackless_exception() -> None:
    # NOTE: Regression - previously raised `KeyError: 'stacktrace'`
    error = _chained_error_with_tracebackless_cause()
    report_id = save_report('demo', error)

    from dipdup.report import REPORTS_PATH

    path = REPORTS_PATH / f'{report_id}.yaml'
    assert path.exists()
    path.unlink()


@pytest.fixture
def unwritable_reports_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # NOTE: A directory can't be created under a regular file, regardless of permissions
    blocker = tmp_path / 'blocker'
    blocker.touch()
    path = blocker / 'reports'
    monkeypatch.setattr(report, 'REPORTS_PATH', path)
    return path


@pytest.fixture
def atexit_callbacks(monkeypatch: pytest.MonkeyPatch) -> list[Callable[[], Any]]:
    callbacks: list[Callable[[], Any]] = []
    monkeypatch.setattr(atexit, 'register', callbacks.append)
    return callbacks


def test_cli_wrapper_reraises_original_error_when_report_fails(
    unwritable_reports_path: Path,
    atexit_callbacks: list[Callable[[], Any]],
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    error = DatasourceError('Failed to connect: 403', 'tzkt_mainnet')

    async def index(ctx: Any) -> None:
        raise error

    with caplog.at_level(logging.WARNING), pytest.raises(DatasourceError) as excinfo:
        _run_wrapped(index, SimpleNamespace(obj=None))
    assert excinfo.value is error
    assert excinfo.value.__context__ is None
    assert 'Failed to save report' in caplog.text

    # NOTE: Help is still printed, but it doesn't point to a report that doesn't exist
    for callback in atexit_callbacks:
        callback()
    stderr = capsys.readouterr().err
    assert '`tzkt_mainnet` datasource returned an error' in stderr
    assert 'Report saved' not in stderr
    assert not unwritable_reports_path.exists()


def test_cli_wrapper_graceful_stop_when_report_fails(
    unwritable_reports_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(env, 'TEST', False)

    async def run(ctx: Any) -> None:
        pass

    ctx = SimpleNamespace(obj=SimpleNamespace(config=SimpleNamespace(package='demo')))
    with caplog.at_level(logging.WARNING):
        _run_wrapped(run, ctx)
    assert 'Failed to save report' in caplog.text
    assert not unwritable_reports_path.exists()
