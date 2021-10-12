import asyncio
from contextlib import suppress
from os.path import dirname, join

import pyperf  # type: ignore

from dipdup.config import DipDupConfig
from dipdup.dipdup import DipDup
from dipdup.exceptions import ReindexingRequiredError
from dipdup.test import with_operation_index_fuzzer


def add_cmdline_args(cmd, args):
    cmd += ['--quiet']


runner = pyperf.Runner(add_cmdline_args=add_cmdline_args)


paths = [
    join(dirname(__file__), '..', 'integration_tests', name)
    for name in [
        'hic_et_nunc.yml',
    ]
]


async def _match():
    for path in paths:
        config = DipDupConfig.load([path])
        config.database.path = ':memory:'
        config.initialize()

        with with_operation_index_fuzzer(10, 3):
            dipdup = DipDup(config)
            with suppress(ReindexingRequiredError):
                await dipdup.run(True, True)


runner.bench_func('index_match_operations', lambda: asyncio.run(_match()))
