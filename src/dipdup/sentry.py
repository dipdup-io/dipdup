# NOTE: All imports except the basic ones are very lazy in this module. Let's keep it that way.
import asyncio
import hashlib
import logging
import platform
import tempfile
from contextlib import suppress
from functools import partial
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING
from typing import Any

import orjson
import sentry_sdk
import sentry_sdk.consts
import sentry_sdk.serializer
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.atexit import AtexitIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from dipdup import __version__
from dipdup import baking_bad
from dipdup import env
from dipdup.utils.sys import is_shutting_down

if TYPE_CHECKING:
    from dipdup.config import DipDupConfig


_logger = logging.getLogger('dipdup.sentry')


async def _heartbeat() -> None:
    """Restart Sentry session every 24 hours"""
    with suppress(asyncio.CancelledError):
        while True:
            await asyncio.sleep(60 * 60 * 24)
            _logger.info('Reopening Sentry session')
            sentry_sdk.Hub.current.end_session()
            sentry_sdk.Hub.current.flush()
            sentry_sdk.Hub.current.start_session()


def save_crashdump(error: Exception) -> str:
    """Saves a crashdump file with Sentry error data, returns the path to the tempfile"""
    exc_info = sentry_sdk.utils.exc_info_from_error(error)
    event, _ = sentry_sdk.utils.event_from_exception(exc_info)
    event = sentry_sdk.serializer.serialize(event)

    tmp_dir = Path(tempfile.gettempdir()) / 'dipdup' / 'crashdumps'
    tmp_dir.mkdir(parents=True, exist_ok=True)

    crashdump_file = NamedTemporaryFile(
        mode='ab',
        suffix='.json',
        dir=tmp_dir,
        delete=False,
    )
    with crashdump_file as f:
        f.write(
            orjson.dumps(
                event,
                option=orjson.OPT_INDENT_2,
            ),
        )
    return crashdump_file.name


def before_send(
    event: dict[str, Any],
    hint: dict[str, Any],
    crash_reporting: bool,
) -> dict[str, Any] | None:
    # NOTE: Terminated connections, cancelled tasks, etc.
    if is_shutting_down():
        return None

    # NOTE: Skip some reports if Sentry DSN is not set implicitly
    if crash_reporting:
        if env.TEST or env.CI:
            return None

        # NOTE: User-generated events (e.g. from `ctx.logger`)
        if not event.get('logger', 'dipdup').startswith('dipdup'):
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
    crash_reporting = config.advanced.crash_reporting
    dsn = config.sentry.dsn

    if dsn:
        pass
    elif crash_reporting:
        dsn = baking_bad.SENTRY_DSN
    else:
        return

    _logger.info('Crash reporting is enabled: %s', dsn)
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
    before_send_fn = partial(
        before_send,
        crash_reporting=crash_reporting,
    )

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
        if crash_reporting:
            # NOTE: Prevent Sentry from leaking hostnames
            server_name = 'unknown'
        else:
            server_name = platform.node()

    sentry_sdk.init(
        dsn=dsn,
        integrations=integrations,
        attach_stacktrace=attach_stacktrace,
        before_send=before_send_fn,
        release=release,
        environment=environment,
        server_name=server_name,
        # NOTE: Increase __repr__ length limit
        max_value_length=sentry_sdk.consts.DEFAULT_MAX_VALUE_LENGTH * 10,
    )

    # NOTE: Setting session tags
    tags = {
        'python': platform.python_version(),
        'os': f'{platform.system().lower()}-{platform.machine()}',
        'version': __version__,
        'package': package,
        'release': release,
        'environment': environment,
        'server_name': server_name,
        'crash_reporting': crash_reporting,
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
