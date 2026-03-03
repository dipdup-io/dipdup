from typing import Any
from typing import cast

from dipdup.config.evm_sourcify import EvmSourcifyDatasourceConfig
from dipdup.datasources import AbiDatasource


class EvmSourcifyDatasource(AbiDatasource[EvmSourcifyDatasourceConfig]):
    async def run(self) -> None:
        pass

    async def get_abi(self, address: str) -> dict[str, Any] | list[Any]:
        response = await self.request(
            'get',
            url=f'v2/contract/{self._config.chain_id}/{address}',
            params={
                'fields': 'abi',
            },
        )
        return cast('list[Any]', response['abi'])
