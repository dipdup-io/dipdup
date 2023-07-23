# NOTE: All imports except the basic ones are very lazy in this module. Let's keep it that way.
import asyncio
import hashlib
import logging
import platform
from contextlib import suppress
from typing import Any

import sentry_sdk
import sentry_sdk.serializer
import sentry_sdk.utils
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.atexit import AtexitIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from dipdup import __version__
from dipdup import env
from dipdup.config import DipDupConfig
from dipdup.sys import is_shutting_down

_logger = logging.getLogger(__name__)


async def _heartbeat() -> None:
    """Restart Sentry session every 24 hours"""
    with suppress(asyncio.CancelledError):
        while True:
            await asyncio.sleep(60 * 60 * 24)
            _logger.info('Reopening Sentry session')
            sentry_sdk.Hub.current.end_session()
            sentry_sdk.Hub.current.flush()
            sentry_sdk.Hub.current.start_session()


def extract_event(error: Exception) -> dict[str, Any]:
    """Extracts Sentry event from an exception"""
    exc_info = sentry_sdk.utils.exc_info_from_error(error)
    event, _ = sentry_sdk.utils.event_from_exception(exc_info)
    event = sentry_sdk.serializer.serialize(event)
    event.pop('_meta', None)
    return event


def before_send(
    event: dict[str, Any],
    hint: dict[str, Any],
) -> dict[str, Any] | None:
    # NOTE: Terminated connections, cancelled tasks, etc.
    if is_shutting_down():
        return None

    # NOTE: Dark magic ahead. Merge `CallbackError` and its cause when possible.
    with suppress(KeyError, IndexError):
        exceptions = event['exception']['values']
        if exceptions[-1]['type'] == 'CallbackError':
            wrapper_frames = exceptions[-1]['stacktrace']['frames']
            crash_frames = exceptions[-2]['stacktrace']['frames']
            exceptions[-2]['stacktrace']['frames'] = wrapper_frames + crash_frames
            event['message'] = exceptions[-2]['value']
            del exceptions[-1]

    return event


def init_sentry(config: 'DipDupConfig') -> None:
    dsn = config.sentry.dsn
    if dsn:
        _logger.info('Sentry is enabled: %s', dsn)

    if config.sentry.debug:
        level, event_level, attach_stacktrace = logging.DEBUG, logging.WARNING, True
    else:
        level, event_level, attach_stacktrace = logging.INFO, logging.ERROR, False

    integrations = [
        AioHttpIntegration(),
        LoggingIntegration(
            level=level,
            event_level=event_level,
        ),
        # NOTE: Suppresses `atexit` notification
        AtexitIntegration(lambda _, __: None),
    ]
    package = config.package or 'dipdup'
    release = config.sentry.release or __version__
    environment = config.sentry.environment
    server_name = config.sentry.server_name

    if not environment:
        if env.DOCKER:
            environment = 'docker'
        elif env.TEST:
            environment = 'tests'
        elif env.CI:
            environment = 'gha'
        else:
            environment = 'local'

    if not server_name:
        server_name = platform.node()

    sentry_sdk.init(
        dsn=dsn,
        integrations=integrations,
        attach_stacktrace=attach_stacktrace,
        before_send=before_send,
        release=release,
        environment=environment,
        server_name=server_name,
    )
    # NOTE: Increase __repr__ length limit
    sentry_sdk.utils.MAX_STRING_LENGTH *= 10

    # NOTE: Setting session tags
    tags = {
        'python': platform.python_version(),
        'os': f'{platform.system().lower()}-{platform.machine()}',
        'version': __version__,
        'package': package,
        'release': release,
        'environment': environment,
        'server_name': server_name,
    }
    _logger.debug('Sentry tags: %s', ', '.join(f'{k}={v}' for k, v in tags.items()))
    for tag, value in tags.items():
        sentry_sdk.set_tag(f'dipdup.{tag}', value)

    # NOTE: User ID allows to track release adoption. It's sent on every session,
    # NOTE: but obfuscated below, so it's not a privacy issue. However, randomly
    # NOTE: generated Docker hostnames may spoil this metric.
    user_id = config.sentry.user_id
    if user_id is None:
        user_id = package + environment + server_name
        user_id = hashlib.sha256(user_id.encode()).hexdigest()[:8]
    _logger.debug('Sentry user_id: %s', user_id)

    sentry_sdk.set_user({'id': user_id})
    sentry_sdk.Hub.current.start_session()
    asyncio.ensure_future(_heartbeat())
