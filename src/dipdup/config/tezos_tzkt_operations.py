from __future__ import annotations

from dataclasses import field
from typing import Any
from typing import Iterator
from typing import Literal
from typing import cast

from pydantic.dataclasses import dataclass

from dipdup.config import CodegenMixin
from dipdup.config import ContractConfig
from dipdup.config import HandlerConfig
from dipdup.config import IndexConfig
from dipdup.config import ParameterTypeMixin
from dipdup.config import StorageTypeMixin
from dipdup.config import SubgroupIndexMixin
from dipdup.config import TzktIndexConfig
from dipdup.config.tzkt import TzktDatasourceConfig
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import FrameworkException
from dipdup.models.tzkt import OperationType
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal


class PatternConfig(CodegenMixin):
    """Base class for pattern config items.

    Contains methods for import and method signature generation during handler callbacks codegen.
    """

    @classmethod
    def format_storage_import(
        cls,
        package: str,
        module_name: str,
    ) -> tuple[str, str]:
        storage_cls = f'{snake_to_pascal(module_name)}Storage'
        return f'{package}.types.{module_name}.storage', storage_cls

    @classmethod
    def format_parameter_import(
        cls,
        package: str,
        module_name: str,
        entrypoint: str,
        alias: str | None,
    ) -> tuple[str, str]:
        entrypoint = entrypoint.lstrip('_')
        parameter_module = pascal_to_snake(entrypoint)
        parameter_cls = f'{snake_to_pascal(entrypoint)}Parameter'
        if alias:
            parameter_cls += f' as {snake_to_pascal(alias)}Parameter'

        return f'{package}.types.{module_name}.parameter.{parameter_module}', parameter_cls

    @classmethod
    def format_untyped_operation_import(cls) -> tuple[str, str]:
        return 'dipdup.models.tzkt', 'OperationData'

    @classmethod
    def format_origination_argument(
        cls,
        module_name: str,
        optional: bool,
        alias: str | None,
    ) -> tuple[str, str]:
        arg_name = pascal_to_snake(alias or f'{module_name}_origination')
        storage_cls = f'{snake_to_pascal(module_name)}Storage'
        if optional:
            return arg_name, f'Origination[{storage_cls}] | None'
        return arg_name, f'Origination[{storage_cls}]'

    @classmethod
    def format_operation_argument(
        cls,
        module_name: str,
        entrypoint: str,
        optional: bool,
        alias: str | None,
    ) -> tuple[str, str]:
        arg_name = pascal_to_snake(alias or entrypoint)
        entrypoint = entrypoint.lstrip('_')
        parameter_cls = f'{snake_to_pascal(arg_name)}Parameter'
        storage_cls = f'{snake_to_pascal(module_name)}Storage'
        if optional:
            return arg_name, f'Transaction[{parameter_cls}, {storage_cls}] | None'
        return arg_name, f'Transaction[{parameter_cls}, {storage_cls}]'

    @classmethod
    def format_untyped_operation_argument(
        cls,
        type_: str,
        subgroup_index: int,
        optional: bool,
        alias: str | None,
    ) -> tuple[str, str]:
        arg_name = pascal_to_snake(alias or f'{type_}_{subgroup_index}')
        if optional:
            return arg_name, 'OperationData | None'
        return arg_name, 'OperationData'


@dataclass
class OperationHandlerTransactionPatternConfig(PatternConfig, StorageTypeMixin, ParameterTypeMixin, SubgroupIndexMixin):
    """Operation handler pattern config

    :param type: always 'transaction'
    :param source: Match operations by source contract alias
    :param destination: Match operations by destination contract alias
    :param entrypoint: Match operations by contract entrypoint
    :param optional: Whether can operation be missing in operation group
    :param alias: Alias for transaction (helps to avoid duplicates)
    """

    type: Literal['transaction'] = 'transaction'
    source: ContractConfig | None = None
    destination: ContractConfig | None = None
    entrypoint: str | None = None
    optional: bool = False
    alias: str | None = None

    def __post_init_post_parse__(self) -> None:
        StorageTypeMixin.__post_init_post_parse__(self)
        ParameterTypeMixin.__post_init_post_parse__(self)
        SubgroupIndexMixin.__post_init_post_parse__(self)
        if self.entrypoint and not self.destination:
            raise ConfigurationError('Transactions with entrypoint must also have destination')

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        if self.typed_contract:
            module_name = self.typed_contract.module_name
            yield 'dipdup.models.tzkt', 'Transaction'
            yield self.format_parameter_import(
                package,
                module_name,
                cast(str, self.entrypoint),
                self.alias,
            )
            yield self.format_storage_import(package, module_name)
        else:
            yield self.format_untyped_operation_import()

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        if self.typed_contract:
            module_name = self.typed_contract.module_name
            yield self.format_operation_argument(
                module_name,
                cast(str, self.entrypoint),
                self.optional,
                self.alias,
            )
        else:
            yield self.format_untyped_operation_argument(
                'transaction',
                self.subgroup_index,
                self.optional,
                self.alias,
            )

    @property
    def typed_contract(self) -> ContractConfig | None:
        if self.entrypoint and self.destination:
            return self.destination
        return None


@dataclass
class OperationHandlerOriginationPatternConfig(PatternConfig, StorageTypeMixin, SubgroupIndexMixin):
    """Origination handler pattern config

    :param type: always 'origination'
    :param source: Match operations by source contract alias
    :param similar_to: Match operations which have the same code/signature (depending on `strict` field)
    :param originated_contract: Match origination of exact contract
    :param optional: Whether can operation be missing in operation group
    :param strict: Match operations by storage only or by the whole code
    :param alias: Alias for transaction (helps to avoid duplicates)
    """

    type: Literal['origination'] = 'origination'
    source: ContractConfig | None = None
    similar_to: ContractConfig | None = None
    originated_contract: ContractConfig | None = None
    optional: bool = False
    strict: bool = False
    alias: str | None = None

    def __post_init_post_parse__(self) -> None:
        super().__post_init_post_parse__()
        if not self.similar_to:
            return

        self.originated_contract = self.similar_to
        self.similar_to = None

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        if self.typed_contract:
            module_name = self.typed_contract.module_name
            yield 'dipdup.models.tzkt', 'Origination'
            yield self.format_storage_import(package, module_name)
        else:
            yield 'dipdup.models.tzkt', 'OperationData'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        if self.typed_contract:
            yield self.format_origination_argument(
                self.typed_contract.module_name,
                self.optional,
                self.alias,
            )
        else:
            yield self.format_untyped_operation_argument(
                'origination',
                self.subgroup_index,
                self.optional,
                self.alias,
            )

    @property
    def typed_contract(self) -> ContractConfig | None:
        if self.originated_contract:
            return self.originated_contract
        # TODO: Remove in 7.0
        if self.similar_to:
            raise FrameworkException
        return None


@dataclass
class TezosTzktOperationsIndexConfig(TzktIndexConfig):
    """Operation index config

    :param kind: always `operation`
    :param datasource: Alias of index datasource in `datasources` section
    :param handlers: List of indexer handlers
    :param types: Types of transaction to fetch
    :param contracts: Aliases of contracts being indexed in `contracts` section
    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing at
    """

    kind: Literal['tezos.tzkt.operations']
    handlers: tuple[TezosTzktOperationHandlerConfig, ...]
    contracts: list[ContractConfig] = field(default_factory=list)
    types: tuple[OperationType, ...] = (OperationType.transaction,)

    first_level: int = 0
    last_level: int = 0

    @classmethod
    def strip(cls, config_dict: dict[str, Any]) -> None:
        super().strip(config_dict)
        for handler in config_dict['handlers']:
            for item in handler['pattern']:
                item.pop('alias', None)

    def import_objects(self, package: str) -> None:
        for handler_config in self.handlers:
            handler_config.initialize_callback_fn(package)

            for pattern_config in handler_config.pattern:
                typed_contract = pattern_config.typed_contract
                if not typed_contract:
                    continue

                module_name = typed_contract.module_name
                pattern_config.initialize_storage_cls(package, module_name)

                if isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
                    pattern_config.initialize_parameter_cls(
                        package,
                        module_name,
                        cast(str, pattern_config.entrypoint),
                    )


OperationHandlerPatternConfigU = OperationHandlerOriginationPatternConfig | OperationHandlerTransactionPatternConfig


@dataclass
class TezosTzktOperationHandlerConfig(HandlerConfig, kind='handler'):
    """Operation handler config

    :param callback: Callback name
    :param pattern: Filters to match operation groups
    """

    pattern: tuple[OperationHandlerPatternConfigU, ...]

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        for pattern in self.pattern:
            yield from pattern.iter_imports(package)

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'

        arg_names: set[str] = set()
        for pattern in self.pattern:
            arg, arg_type = next(pattern.iter_arguments())
            if arg in arg_names:
                raise ConfigurationError(
                    f'Pattern item is not unique. Set `alias` field to avoid duplicates.\n\n              handler: `{self.callback}`\n              entrypoint: `{arg}`',
                )
            arg_names.add(arg)
            yield arg, arg_type


@dataclass
class OperationUnfilteredHandlerConfig(HandlerConfig, kind='handler'):
    """Handler of unfiltered operation index

    :param callback: Callback name
    """

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.tzkt', 'OperationData'
        yield package, 'models as models'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield 'operation', 'OperationData'


@dataclass
class TezosTzktOperationsUnfilteredIndexConfig(TzktIndexConfig):
    """Operation index config

    :param kind: always `operation_unfiltered`
    :param datasource: Alias of index datasource in `datasources` section
    :param callback: Callback name
    :param types: Types of transaction to fetch

    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing at
    """

    kind: Literal['tezos.tzkt.operations_unfiltered']
    datasource: TzktDatasourceConfig
    callback: str
    types: tuple[OperationType, ...] = (OperationType.transaction,)

    first_level: int = 0
    last_level: int = 0

    def __post_init_post_parse__(self) -> None:
        super().__post_init_post_parse__()
        self.handler_config = OperationUnfilteredHandlerConfig(callback=self.callback)

    def import_objects(self, package: str) -> None:
        self.handler_config.initialize_callback_fn(package)


TezosTzktOperationHandlerConfigU = TezosTzktOperationHandlerConfig | OperationUnfilteredHandlerConfig
TezosTzktOperationsIndexConfigU = TezosTzktOperationsIndexConfig | TezosTzktOperationsUnfilteredIndexConfig
HandlerPatternConfigU = OperationHandlerOriginationPatternConfig | OperationHandlerTransactionPatternConfig
