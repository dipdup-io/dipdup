import json
import logging
from os.path import dirname, join
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from tortoise import Tortoise

from dipdup.config import HasuraConfig, PostgresDatabaseConfig
from dipdup.hasura import HasuraManager
from dipdup.utils import tortoise_wrapper

logging.basicConfig()
logging.getLogger().setLevel(0)


class HasuraTest(IsolatedAsyncioTestCase):
    async def test_configure_hasura(self):

        with open(join(dirname(__file__), 'hasura', 'empty.json')) as file:
            empty_metadata = json.load(file)
        with open(join(dirname(__file__), 'hasura', 'query_dipdup_state.json')) as file:
            query_dipdup_state = json.load(file)
        with open(join(dirname(__file__), 'hasura', 'query_holder.json')) as file:
            query_holder = json.load(file)
        with open(join(dirname(__file__), 'hasura', 'query_swap.json')) as file:
            query_swap = json.load(file)
        with open(join(dirname(__file__), 'hasura', 'query_token.json')) as file:
            query_token = json.load(file)
        with open(join(dirname(__file__), 'hasura', 'query_trade.json')) as file:
            query_trade = json.load(file)
        with open(join(dirname(__file__), 'hasura', 'replace_metadata_request.json')) as file:
            replace_metadata_request = json.load(file)

        async with tortoise_wrapper('sqlite://:memory:', 'demo_hic_et_nunc.models'):
            await Tortoise.generate_schemas()

            database_config = PostgresDatabaseConfig(kind='postgres', host='', port=0, user='', database='', schema_name='hic_et_nunc')
            hasura_config = HasuraConfig('http://localhost')

            hasura_manager = HasuraManager('demo_hic_et_nunc', hasura_config, database_config)
            hasura_manager._get_views = AsyncMock(return_value=[])
            hasura_manager._proxy = Mock()
            hasura_manager._proxy.http_request = AsyncMock(
                side_effect=[
                    empty_metadata,
                    {},
                    query_dipdup_state,
                    query_holder,
                    query_swap,
                    query_token,
                    query_trade,
                    {},
                ]
            )
            hasura_manager._healthcheck = AsyncMock()

            await hasura_manager.configure()

            self.assertEqual(hasura_manager._proxy.http_request.call_args[-1]['json'], replace_metadata_request)
