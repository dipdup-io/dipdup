import asyncio
from contextlib import suppress
import json
import logging
from os.path import join
from aiohttp import ClientConnectorError, ClientOSError
from dipdup.config import DipDupConfig
from dipdup.exceptions import ConfigurationError
from dipdup.utils import http_request


_logger = logging.getLogger(__name__)


async def configure_hasura(config: DipDupConfig):

    if config.hasura is None:
        raise ConfigurationError('`hasura` config section missing')

    _logger.info('Loading metadata file')
    url = config.hasura.url.rstrip("/")
    hasura_metadata_path = join(config.package_path, 'hasura_metadata.json')
    with open(hasura_metadata_path) as file:
        hasura_metadata = json.load(file)

    _logger.info('Waiting for Hasura instance to be healthy')
    for _ in range(60):
        with suppress(ClientConnectorError, ClientOSError):
            async with http_request('get', url=f'{url}/healthz') as response:
                if response.status == 200:
                    break
        await asyncio.sleep(1)
    else:
        _logger.error('Hasura instance not responding for 60 seconds')
        return

    _logger.info('Sending replace metadata request')
    headers = {}
    if config.hasura.admin_secret:
        headers['X-Hasura-Admin-Secret'] = config.hasura.admin_secret
    async with http_request(
        'post',
        url=f'{url}/v1/query',
        data=json.dumps(
            {
                "type": "replace_metadata",
                "args": hasura_metadata,
            },
        ),
        headers=headers,
    ) as response:
        result = await response.json()
        if not result.get('message') == 'success':
            _logger.error('Can\'t configure Hasura instance: %s', result)
