import sys
from contextlib import suppress
from os.path import dirname, join
from shutil import rmtree
from unittest import IsolatedAsyncioTestCase

from dipdup import __version__
from dipdup.config import DipDupConfig
from dipdup.dipdup import DipDup


class CodegenTest(IsolatedAsyncioTestCase):
    async def test_codegen(self):
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
                config.initialize(skip_imports=True)
                config.package = 'tmp_test_dipdup'

                if config.package in sys.modules:
                    del sys.modules[config.package]

                try:
                    dipdup = DipDup(config)
                    await dipdup.init()
                    await dipdup.docker_init('dipdup', __version__, 'dipdup.env')
                except Exception as exc:
                    with suppress(FileNotFoundError):
                        rmtree('tmp_test_dipdup')
                    raise exc
                else:
                    with suppress(FileNotFoundError):
                        rmtree('tmp_test_dipdup')
