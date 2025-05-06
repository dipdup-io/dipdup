from pathlib import Path
from typing import Any

from dipdup.codegen import CodeGenerator
from dipdup.config import EvmIndexConfigU
from dipdup.config import HandlerConfig
from dipdup.config.evm import EvmIndexConfig
from dipdup.config.evm_blockvision import EvmBlockvisionDatasourceConfig
from dipdup.config.evm_etherscan import EvmEtherscanDatasourceConfig
from dipdup.config.evm_events import EvmEventsHandlerConfig
from dipdup.config.evm_events import EvmEventsIndexConfig
from dipdup.config.evm_sourcify import EvmSourcifyDatasourceConfig
from dipdup.config.evm_transactions import EvmTransactionsHandlerConfig
from dipdup.config.evm_transactions import EvmTransactionsIndexConfig
from dipdup.datasources import AbiDatasource
from dipdup.exceptions import ConfigurationError
from dipdup.package import EVM_ABI_JSON
from dipdup.utils import json_dumps
from dipdup.utils import snake_to_pascal
from dipdup.utils import touch


class EvmCodeGenerator(CodeGenerator):
    kind = 'evm'

    async def generate_abis(self) -> None:
        for index_config in self._config.indexes.values():
            if isinstance(index_config, EvmIndexConfig):
                await self._fetch_abi(index_config)

    async def generate_schemas(self) -> None:
        from dipdup.abi.evm import abi_to_jsonschemas

        self._cleanup_schemas()

        handler_config: HandlerConfig
        events: set[str] = set()
        methods: set[str] = set()

        for index_config in self._config.indexes.values():
            if isinstance(index_config, EvmEventsIndexConfig):
                for handler_config in index_config.handlers:
                    events.add(handler_config.name)
            elif isinstance(index_config, EvmTransactionsIndexConfig):
                for handler_config in index_config.handlers:
                    if handler_config.typed_contract:
                        # FIXME: Can break when there are multiple signatures for the same method. Forbidden in validation.
                        methods.add(handler_config.cropped_method)

        abi_to_jsonschemas(self._package, events, methods)

    async def _fetch_abi(self, index_config: EvmIndexConfigU) -> None:
        datasources: list[AbiDatasource[Any]] = []
        for datasource_config in index_config.datasources:
            if not isinstance(
                datasource_config,
                EvmEtherscanDatasourceConfig | EvmSourcifyDatasourceConfig | EvmBlockvisionDatasourceConfig,
            ):
                continue
            datasources.append(self._datasources[datasource_config.name])  # type: ignore[arg-type]

        for handler_config in index_config.handlers:
            if isinstance(handler_config, EvmEventsHandlerConfig) and handler_config.contract:
                contract = handler_config.contract
            elif isinstance(handler_config, EvmTransactionsHandlerConfig) and handler_config.typed_contract:
                contract = handler_config.typed_contract
            else:
                continue

            abi_path = self._package.abi / contract.module_name / EVM_ABI_JSON
            if abi_path.exists():
                continue

            if not datasources:
                msg = f'ABI not found at `{abi_path}` and no EVM ABI datasources configured to fetch it'
                raise ConfigurationError(msg)

            abi_json = await self._lookup_abi(contract, datasources)
            touch(abi_path)
            abi_path.write_bytes(json_dumps(abi_json))

    def get_typeclass_name(self, schema_path: Path) -> str:
        module_name = schema_path.stem
        if schema_path.parent.name == 'evm_events':
            class_name = f'{module_name}_payload'
        elif schema_path.parent.name == 'evm_transactions':
            class_name = f'{module_name}_input'
        else:
            class_name = module_name
        return snake_to_pascal(class_name)

    async def _generate_type(self, schema_path: Path, force: bool) -> None:
        markers = {
            'evm_events',
            'evm_transactions',
        }
        if not set(schema_path.parts).intersection(markers):
            return
        await super()._generate_type(schema_path, force)
