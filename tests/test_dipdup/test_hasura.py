import json
from os.path import dirname, join
from unittest import IsolatedAsyncioTestCase

from dipdup.config import DipDupConfig
from dipdup.hasura import generate_hasura_metadata
from demo_hic_et_nunc.models import *


class ConfigTest(IsolatedAsyncioTestCase):
    maxDiff = None

    async def asyncSetUp(self):
        self.path = join(dirname(__file__), 'dipdup.yml')

    async def test_generate_hasura_metadata(self):
        with open(join(dirname(__file__), 'hasura-metadata.json')) as file:
            expected_metadata = json.load(file)
        config = DipDupConfig.load(self.path)
        metadata = await generate_hasura_metadata(config)
        self.assertDictEqual(expected_metadata, metadata)
