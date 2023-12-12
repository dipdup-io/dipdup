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

from dipdup.config import DipDupConfig
from dipdup.config import HasuraConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.dipdup import DipDup
from dipdup.exceptions import FrameworkException
from dipdup.index import Index
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
    dispatcher._indexes[name] = dispatcher._ctx._pending_indexes.pop()
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


async def run_postgres_container() -> PostgresDatabaseConfig:
    """Run Postgres container (destroyed on exit) and return database config with its IP."""
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
    )
    atexit.register(postgres_container.stop)
    postgres_container.reload()
    postgres_ip = postgres_container.attrs['NetworkSettings']['IPAddress']

    while not postgres_container.exec_run('pg_isready').exit_code == 0:
        await asyncio.sleep(0.1)

    return PostgresDatabaseConfig(
        kind='postgres',
        host=postgres_ip,
        port=5432,
        user='test',
        database='test',
        password='test',
    )


async def run_hasura_container(postgres_ip: str) -> HasuraConfig:
    """Run Hasura container (destroyed on exit) and return config with its IP."""
    docker = get_docker_client()
    hasura_container = docker.containers.run(
        image=get_default_answers()['hasura_image'],
        environment={
            'HASURA_GRAPHQL_DATABASE_URL': f'postgres://test:test@{postgres_ip}:5432',
        },
        detach=True,
        remove=True,
    )
    atexit.register(hasura_container.stop)
    hasura_container.reload()
    hasura_ip = hasura_container.attrs['NetworkSettings']['IPAddress']

    return HasuraConfig(
        url=f'http://{hasura_ip}:8080',
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
        config, _ = DipDupYAMLConfig.load(config_paths, environment=False)
        tmp_config_path = Path(tmp_package_path) / 'dipdup.yaml'
        tmp_config_path.write_text(config.dump())

        # NOTE: Symlink packages and executables
        tmp_bin_path = Path(tmp_package_path) / 'bin'
        tmp_bin_path.mkdir()
        for executable in ('dipdup', 'datamodel-codegen'):
            if (executable_path := which(executable)) is None:
                raise FrameworkException(f'Executable `{executable}` not found')  # pragma: no cover
            os.symlink(executable_path, tmp_bin_path / executable)

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
            **os.environ,
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
    tmp_config_path = Path(tmp_path) / 'dipdup.yaml'

    proc = await asyncio.subprocess.create_subprocess_shell(
        f'dipdup -c {tmp_config_path} {" ".join(args)}',
        cwd=tmp_path,
        shell=True,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    res = await proc.communicate()
    if proc.returncode != 0:
        raise Exception(f'`dipdup` failed: {res[0].decode()}\n{res[1].decode()}')
