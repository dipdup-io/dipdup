import atexit
import logging
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import click
import pytest

from dipdup import env
from dipdup.cli import _cli_wrapper

CTX = SimpleNamespace(obj=SimpleNamespace(config=SimpleNamespace(package='demo')))


class _Crash(Exception): ...


@pytest.fixture
def atexit_callbacks(monkeypatch: pytest.MonkeyPatch) -> list[Callable[[], Any]]:
    callbacks: list[Callable[[], Any]] = []
    monkeypatch.setattr(atexit, 'register', callbacks.append)
    return callbacks


@pytest.fixture
def reports_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / 'reports'
    monkeypatch.setattr('dipdup.report.REPORTS_PATH', path)
    return path


@pytest.fixture
def unwritable_reports_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # NOTE: A regular file where a directory is expected; `mkdir` fails with an `OSError` even as root
    blocker = tmp_path / 'blocker'
    blocker.touch()
    path = blocker / 'reports'
    monkeypatch.setattr('dipdup.report.REPORTS_PATH', path)
    return path


def _wrap(fn: Callable[..., Any]) -> Callable[..., None]:
    # NOTE: `_cli_wrapper` is typed as returning the async command, but the wrapper itself is sync
    return _cli_wrapper(fn)


def _crashing(error: Exception) -> Callable[..., None]:
    async def command(ctx: Any) -> None:
        raise error

    return _wrap(command)


def test_crash_report_saved(
    reports_path: Path,
    atexit_callbacks: list[Callable[[], Any]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    error = _Crash('boom')
    with pytest.raises(_Crash) as exc_info:
        _crashing(error)(CTX)
    assert exc_info.value is error

    (report,) = reports_path.glob('*.yaml')
    for callback in atexit_callbacks:
        callback()
    stderr = capsys.readouterr().err
    assert f'Report saved; run `dipdup report show {report.stem}`' in stderr


def test_crash_report_unwritable_keeps_original_error(
    unwritable_reports_path: Path,
    atexit_callbacks: list[Callable[[], Any]],
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = _Crash('boom')
    with caplog.at_level(logging.WARNING), pytest.raises(_Crash) as exc_info:
        _crashing(error)(CTX)
    assert exc_info.value is error
    assert any('report' in r.getMessage().lower() for r in caplog.records if r.levelno == logging.WARNING)

    assert atexit_callbacks, 'help for the original error is not scheduled'
    for callback in atexit_callbacks:
        callback()
    stderr = capsys.readouterr().err
    assert 'Report saved' not in stderr
    assert stderr.strip(), 'help for the original error is not printed'


def test_run_shutdown_report_unwritable(
    unwritable_reports_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(env, 'TEST', False)

    async def run(ctx: Any) -> None:
        return None

    with caplog.at_level(logging.WARNING):
        _wrap(run)(CTX)
    assert any('report' in r.getMessage().lower() for r in caplog.records if r.levelno == logging.WARNING)


def test_usage_error_has_no_report(reports_path: Path, atexit_callbacks: list[Callable[[], Any]]) -> None:
    with pytest.raises(click.UsageError):
        _crashing(click.UsageError('bad flag'))(CTX)
    assert not reports_path.exists()
    assert not atexit_callbacks
