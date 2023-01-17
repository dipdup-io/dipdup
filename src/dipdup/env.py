import platform
from os import environ as env
from pathlib import Path


def get(key: str, default: str | None = None) -> str | None:
    return env.get(key, default)


def get_bool(key: str, default: bool = False) -> bool:
    return get(key) in ('1', 'true', 'True')


def get_int(key: str, default: int) -> int:
    return int(get(key) or default)


def in_tests() -> None:
    global TEST, REPLAY_PATH
    TEST = True
    REPLAY_PATH = str(Path(__file__).parent.parent.parent.parent / 'tests' / 'replays')
    env['DIPDUP_REPLAY_PATH'] = REPLAY_PATH


if env.get('CI') == 'true':
    env['DIPDUP_CI'] = '1'
if platform.system() == 'Linux' and Path('/.dockerenv').exists():
    env['DIPDUP_DOCKER'] = '1'

TEST = get_bool('DIPDUP_TEST')
CI = get_bool('DIPDUP_CI')
DOCKER = get_bool('DIPDUP_DOCKER')
NEXT = get_bool('DIPDUP_NEXT')
DOCKER_IMAGE = get('DIPDUP_DOCKER_IMAGE')
REPLAY_PATH = get('DIPDUP_REPLAY_PATH')
