from contextlib import suppress
from pathlib import Path
from shutil import rmtree
from unittest import IsolatedAsyncioTestCase

from dipdup.config import DipDupConfig
from dipdup.dipdup import DipDup

configs = [
    'hic_et_nunc',
    'quipuswap',
    'tzcolors',
    'tezos_domains_big_map',
    'registrydao',
]


class CodegenTest(IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        for name in configs:
            with suppress(FileNotFoundError):
                package_path = f'demo_{name}_tmp'
                rmtree(package_path)

    async def test_codegen(self) -> None:
        for name in configs:
            config_path = Path(__file__).parent / f'{name}.yml'
            config = DipDupConfig.load([config_path])
            config.package += '_tmp'
            config.initialize(skip_imports=True)

            dipdup = DipDup(config)
            await dipdup.init()
