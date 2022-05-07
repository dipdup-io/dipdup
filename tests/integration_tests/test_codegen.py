import sys
from contextlib import suppress
from os.path import dirname
from os.path import join
from shutil import rmtree
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from dipdup.config import DipDupConfig
from dipdup.dipdup import DipDup
from dipdup.utils import skip_ci


@skip_ci
class CodegenTest(IsolatedAsyncioTestCase):
    async def test_codegen(self) -> None:
        for name in [
            'hic_et_nunc.yml',
            'quipuswap.yml',
            'tzcolors.yml',
            'tezos_domains_big_map.yml',
            'registrydao.yml',
        ]:
            with self.subTest(name):
                config_path = join(dirname(__file__), name)
                config = DipDupConfig.load([config_path])
                config.package += '_tmp'
                config.initialize(skip_imports=True)

                try:
                    dipdup = DipDup(config)
                    await dipdup.init()
                finally:
                    rmtree(config.package_path)
