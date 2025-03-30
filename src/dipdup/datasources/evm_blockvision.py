from typing import Any
from typing import cast

import orjson

from dipdup.config.evm_blockvision import EvmBlockvisionDatasourceConfig
from dipdup.datasources import AbiDatasource


class EvmBlockvisionDatasource(AbiDatasource[EvmBlockvisionDatasourceConfig]):
    async def run(self) -> None:
        pass

    async def get_abi(self, address: str) -> dict[str, Any] | list[Any]:
        response = await self.request(
            'get',
            url='verifyContractV2/data',
            params={'address': address},
        )
        return cast('list[Any]', orjson.loads(response['result']['contractABI']))
