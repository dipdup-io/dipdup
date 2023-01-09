import asyncio
import logging
import platform
import signal
import sys
import warnings
from os import environ as env
from pathlib import Path

# NOTE: Do not try to load config for these commands as they don't need it
IGNORE_CONFIG_CMDS = {'new', 'install', 'uninstall', 'update'}
# NOTE: Our signal handler conflicts with Click's one in prompt mode
IGNORE_SIGINT_CMDS = {*IGNORE_CONFIG_CMDS, None, 'schema', 'wipe'}

_is_shutting_down = False
_logger = logging.getLogger('dipdup.cli')


async def _shutdown() -> None:  # pragma: no cover
    global _is_shutting_down
    if _is_shutting_down:
        return
    _is_shutting_down = True

    _logger.info('Shutting down')
    tasks = filter(lambda t: t != asyncio.current_task(), asyncio.all_tasks())
    list(map(asyncio.Task.cancel, tasks))
    await asyncio.gather(*tasks, return_exceptions=True)


def is_shutting_down() -> bool:
    return _is_shutting_down


def is_in_tests() -> bool:
    return env.get('DIPDUP_TEST', '0') == '1'


def is_in_ci() -> bool:
    return env.get('CI') == 'true'


def is_in_docker() -> bool:
    return platform.system() == 'Linux' and Path('/.dockerenv').exists()


def set_in_tests() -> None:
    env['DIPDUP_TEST'] = '1'
    env['DIPDUP_REPLAY_PATH'] = str(Path(__file__).parent.parent.parent.parent / 'tests' / 'replays')


def set_up_logging() -> None:
    root = logging.getLogger()
    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter('%(levelname)-8s %(name)-20s %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # NOTE: Nothing useful there
    logging.getLogger('tortoise').setLevel(logging.WARNING)


def set_up_process(cmd: str | None) -> None:
    """Set up interpreter process-wide state"""
    # NOTE: Skip for integration tests
    if is_in_tests():
        return

    # NOTE: Register shutdown handler for non-interactive commands (avoiding conflicts with Click prompts)
    if cmd not in IGNORE_SIGINT_CMDS:
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(
            signal.SIGINT,
            lambda: asyncio.ensure_future(_shutdown()),
        )

    # NOTE: Better discoverability of DipDup packages and configs
    sys.path.append(str(Path.cwd()))
    sys.path.append(str(Path.cwd() / 'src'))

    # NOTE: Format warnings as normal log messages
    logging.captureWarnings(True)
    warnings.simplefilter('always', DeprecationWarning)
    warnings.formatwarning = lambda msg, *a, **kw: str(msg)
