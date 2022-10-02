import os
from contextlib import suppress
from os.path import dirname
from os.path import join
from shutil import rmtree
from unittest import IsolatedAsyncioTestCase

from dipdup.config import DipDupConfig
from dipdup.dipdup import DipDup

configs = [
    'hic_et_nunc',
    'quipuswap',
    'tzcolors',
    'domains_big_map',
    'registrydao',
]


class CodegenTest(IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        for name in configs:
            with suppress(FileNotFoundError):
                package_path = join(os.getcwd(), f'demo_{name}_tmp')
                rmtree(package_path)

    async def test_codegen(self) -> None:
        for name in configs:
            config_path = join(dirname(__file__), name + '.yml')
            config = DipDupConfig.load([config_path])
            config.package += '_tmp'
            config.initialize(skip_imports=True)

            dipdup = DipDup(config)
            await dipdup.init()
