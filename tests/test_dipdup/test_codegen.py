import json
from os import rmdir
from os.path import dirname, join
from shutil import rmtree
from unittest import TestCase
from dipdup import codegen

from dipdup.config import DipDupConfig


class CodegenTest(TestCase):
    def setUp(self):
        self.config_path = join(dirname(__file__), 'config.yml')
        self.config = DipDupConfig.load(self.config_path)
        self.config.package = 'tmp_test_dipdup'

    def test_codegen(self):
        try:
            codegen.create_package(self.config)
            codegen.fetch_schemas()
            codegen.generate_types(self.config)
            codegen.generate_handlers(self.config)
        finally:
            rmtree('tmp_test_dipdup')
            ...
