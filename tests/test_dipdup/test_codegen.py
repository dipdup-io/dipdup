import json
from os.path import dirname, join
from shutil import rmtree
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

from dipdup import codegen
from dipdup.config import DipDupConfig


class CodegenTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.config_path = join(dirname(__file__), 'dipdup.yml')
        self.config = DipDupConfig.load(self.config_path)
        self.config.package = 'tmp_test_dipdup'
        schemas_response_path = join(dirname(__file__), 'test_datasources', 'test_tzkt', 'jsonschema.json')
        with open(schemas_response_path) as file:
            self.fetch_schemas_mock = json.load(file)

    async def test_codegen(self):
        try:
            with patch('dipdup.codegen._fetch_schemas', AsyncMock(return_value=self.fetch_schemas_mock)):
                await codegen.create_package(self.config)
                await codegen.fetch_schemas(self.config)
                await codegen.generate_types(self.config)
                await codegen.generate_handlers(self.config)
        except Exception:
            rmtree('tmp_test_dipdup')
            raise
        else:
            rmtree('tmp_test_dipdup')
