from collections.abc import Iterator
from typing import Any

import pytest
import sentry_sdk
from sentry_sdk.scope import Scope
from sentry_sdk.scope import ScopeType
from sentry_sdk.scope import use_isolation_scope

from dipdup.config import SentryConfig
from dipdup.sentry import init_sentry


@pytest.fixture
def captured_events(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, Any]]]:
    """Init Sentry with event interception (no network) and reset global state afterwards."""
    events: list[dict[str, Any]] = []

    def _before_send(event: Any, hint: Any) -> None:
        events.append(event)
        # NOTE: Returning None drops the event, so nothing is sent over the network

    real_init = sentry_sdk.init

    def _patched_init(*args: Any, **kwargs: Any) -> Any:
        kwargs['before_send'] = _before_send
        return real_init(*args, **kwargs)

    monkeypatch.setattr(sentry_sdk, 'init', _patched_init)

    try:
        yield events
    finally:
        # NOTE: Reset process-wide Sentry state so tags/client don't leak into other tests
        sentry_sdk.get_global_scope().clear()
        sentry_sdk.get_isolation_scope().clear()
        sentry_sdk.get_current_scope().clear()
        real_init(dsn=None)


async def test_dipdup_tags_reach_events_from_foreign_scope(
    captured_events: list[dict[str, Any]],
) -> None:
    # NOTE: Mimic the real startup - init_sentry runs once, synchronously, before indexing
    config = SentryConfig(dsn='https://public@example.com/1')
    init_sentry(config, package='demo_package')

    captured_events.clear()
    # NOTE: Real crashes are captured from a different scope than the startup one
    # NOTE: (excepthook / forked async task). A fresh isolation scope reproduces that path -
    # NOTE: it does NOT inherit tags set on the startup isolation scope.
    with use_isolation_scope(Scope(ty=ScopeType.ISOLATION)):
        sentry_sdk.capture_message('boom')

    assert captured_events, 'event was not captured'
    tags = captured_events[-1].get('tags') or {}
    # NOTE: Regression for #1289 - `dipdup.*` tags were set on the isolation scope and never
    # NOTE: reached events captured from other contexts. They belong on the global scope.
    assert 'dipdup.version' in tags
    assert 'dipdup.package' in tags
    assert tags['dipdup.package'] == 'demo_package'
