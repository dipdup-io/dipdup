"""This module contains helper functions for testing DipDup projects.

These helpers are not part of the public API and can be changed without prior notice.
"""

import asyncio
import atexit
import os
import tempfile
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from contextlib import asynccontextmanager
from pathlib import Path
from shutil import which
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple
from typing import cast

from dipdup.config import DipDupConfig
from dipdup.config import HasuraConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.dipdup import DipDup
from dipdup.exceptions import FrameworkException
from dipdup.index import Index
from dipdup.package import CWD_ENV
from dipdup.project import get_default_answers
from dipdup.yaml import DipDupYAMLConfig

if TYPE_CHECKING:
    from docker.client import DockerClient  # type: ignore[import-untyped]


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
    await dipdup._set_up_hooks()
    await dipdup._initialize_schema()
    await dipdup._set_up_transactions(stack)

    return dipdup


async def spawn_index(dipdup: DipDup, name: str) -> Index[Any, Any, Any]:
    """Spawn index from config and add it to dispatcher."""
    dispatcher = dipdup._index_dispatcher
    index: Index[Any, Any, Any] = await dispatcher._ctx._spawn_index(name)
    dispatcher._indexes[name] = dispatcher._ctx._pending_indexes.get_nowait()
    return index


def get_docker_client() -> 'DockerClient':
    """Get Docker client instance if socket is available; skip test otherwise."""
    import _pytest.outcomes
    from docker.client import DockerClient

    docker_socks = (
        Path('/var/run/docker.sock'),
        Path.home() / 'Library' / 'Containers' / 'com.docker.docker' / 'Data' / 'vms' / '0' / 'docker.sock',
        Path.home() / 'Library' / 'Containers' / 'com.docker.docker' / 'Data' / 'docker.sock',
    )
    for path in docker_socks:
        if path.exists():
            return DockerClient(base_url=f'unix://{path}')

    raise _pytest.outcomes.Skipped(  # pragma: no cover
        'Docker socket not found',
        allow_module_level=True,
    )


# NOTE: Tests connect to containers from the host (not from another container). On native Linux the host can
# NOTE: route to container bridge IPs, but under Docker Desktop (incl. WSL2) it cannot — only published ports on
# NOTE: localhost are reachable. So we publish a random host port and connect via 127.0.0.1, which works in both
# NOTE: setups. Container-to-container traffic (Hasura -> Postgres) still uses the bridge IP (`internal_host`).
def _published_port(container: Any, internal_port: int) -> int:
    """Read the random host port Docker assigned to `internal_port/tcp` (retry until populated)."""
    for _ in range(100):
        container.reload()
        ports = container.attrs['NetworkSettings']['Ports'] or {}
        if mapping := ports.get(f'{internal_port}/tcp'):
            return int(mapping[0]['HostPort'])
        import time

        time.sleep(0.1)
    raise FrameworkException(f'Container did not publish port {internal_port}')


def _container_ip(container: Any) -> str:
    """Bridge IP for container-to-container traffic."""
    network_settings = container.attrs['NetworkSettings']
    ip = network_settings.get('IPAddress') or next(iter(network_settings['Networks'].values()))['IPAddress']
    return cast('str', ip)


async def _wait_tcp(host: str, port: int, timeout: float = 60.0) -> None:
    """Wait until host:port accepts TCP connections (host-side readiness; covers published-port wiring)."""
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=5)
            writer.close()
            await writer.wait_closed()
            return
        except (OSError, TimeoutError) as e:
            if asyncio.get_event_loop().time() > deadline:
                raise FrameworkException(f'`{host}:{port}` not reachable after {timeout}s') from e
            await asyncio.sleep(0.2)


class PostgresContainer(NamedTuple):
    config: PostgresDatabaseConfig
    """Host-facing config (connect from the host via 127.0.0.1:<published port>)."""
    internal_host: str
    """Bridge IP for container-to-container use (e.g. Hasura -> Postgres)."""


async def run_postgres_container() -> PostgresContainer:
    """Run Postgres container (destroyed on exit); reachable from the host via a published port."""
    docker = get_docker_client()
    postgres_container = docker.containers.run(
        image=get_default_answers()['postgres_image'],
        environment={
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
        },
        detach=True,
        remove=True,
        ports={'5432/tcp': None},
    )
    atexit.register(postgres_container.stop)

    host_port = _published_port(postgres_container, 5432)
    internal_host = _container_ip(postgres_container)

    while not postgres_container.exec_run('pg_isready').exit_code == 0:
        await asyncio.sleep(0.1)
    await _wait_tcp('127.0.0.1', host_port)

    return PostgresContainer(
        config=PostgresDatabaseConfig(
            kind='postgres',
            host='127.0.0.1',
            port=host_port,
            user='test',
            database='test',
            password='test',
        ),
        internal_host=internal_host,
    )


async def run_hasura_container(postgres_internal_host: str) -> HasuraConfig:
    """Run Hasura container (destroyed on exit); reachable from the host via a published port.

    `postgres_internal_host` is the Postgres container's bridge IP (container-to-container traffic).
    """
    docker = get_docker_client()
    hasura_container = docker.containers.run(
        image=get_default_answers()['hasura_image'],
        environment={
            'HASURA_GRAPHQL_DATABASE_URL': f'postgres://test:test@{postgres_internal_host}:5432',
        },
        detach=True,
        ports={'8080/tcp': None},
        # remove=True,
    )
    atexit.register(hasura_container.stop)

    host_port = _published_port(hasura_container, 8080)
    await _wait_tcp('127.0.0.1', host_port)

    return HasuraConfig(
        url=f'http://127.0.0.1:{host_port}',
        source='new_source',
        create_source=True,
    )


@asynccontextmanager
async def tmp_project(
    config_paths: list[Path],
    package: str,
    exists: bool,
    env: dict[str, str] | None = None,
) -> AsyncIterator[tuple[Path, dict[str, str]]]:
    """Create a temporary isolated DipDup project."""
    with tempfile.TemporaryDirectory() as tmp_package_path:
        # NOTE: Dump config
        config, _ = DipDupYAMLConfig.load(
            config_paths,
            environment=False,
            raw=True,
            unsafe=False,
        )
        tmp_config_path = Path(tmp_package_path) / 'dipdup.yaml'
        tmp_config_path.write_text(config.dump())

        # NOTE: Symlink packages and executables
        tmp_bin_path = Path(tmp_package_path) / 'bin'
        tmp_bin_path.mkdir()

        if (dipdup_path := which('dipdup')) is None:
            raise FrameworkException('Executable `dipdup` not found')
        os.symlink(dipdup_path, tmp_bin_path / 'dipdup')

        os.symlink(
            Path(__file__).parent.parent / 'dipdup',
            Path(tmp_package_path) / 'dipdup',
        )

        # NOTE: Ensure that `run` uses existing package and `init` creates a new one
        if exists:
            os.symlink(
                Path(__file__).parent.parent / package,
                Path(tmp_package_path) / package,
            )

        # NOTE: Prepare environment
        env = {
            **(env or {}),
            'PATH': str(tmp_bin_path),
            'PYTHONPATH': str(tmp_package_path),
            'DIPDUP_TEST': '1',
            'DIPDUP_DEBUG': '1',
        }

        yield Path(tmp_package_path), env


async def run_in_tmp(
    tmp_path: Path,
    env: dict[str, str],
    *args: str,
) -> None:
    """Run DipDup in existing temporary project."""
    if not (tmp_path / CWD_ENV).exists() and (env_path := Path.cwd().joinpath(CWD_ENV)).exists():
        os.symlink(env_path, tmp_path / CWD_ENV)
    tmp_config_path = Path(tmp_path) / 'dipdup.yaml'
    command = f'dipdup -c {tmp_config_path} {" ".join(args)}'
    proc = await asyncio.subprocess.create_subprocess_shell(
        command,
        cwd=tmp_path,
        shell=True,
        env={
            **os.environ,
            **env,
        },
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    res = await proc.communicate()
    if proc.returncode != 0:
        raise Exception(f'`dipdup` failed: {res[0].decode()}\n{res[1].decode()}')
