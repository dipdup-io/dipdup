from __future__ import annotations

from dataclasses import field
from typing import TYPE_CHECKING
from typing import Any
from typing import Literal
from typing import cast

from pydantic.dataclasses import dataclass

from dipdup.config import CodegenMixin
from dipdup.config import HandlerConfig
from dipdup.config.tezos import TezosContractConfig
from dipdup.config.tezos_tzkt import TzktDatasourceConfig
from dipdup.config.tezos_tzkt import TzktIndexConfig
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import ConfigurationError
from dipdup.models.tezos_tzkt import OriginationSubscription
from dipdup.models.tezos_tzkt import SmartRollupExecuteSubscription
from dipdup.models.tezos_tzkt import TransactionSubscription
from dipdup.models.tezos_tzkt import TzktOperationType
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal

if TYPE_CHECKING:
    from collections.abc import Iterator

    from dipdup.subscriptions import Subscription


@dataclass
class SubgroupIndexMixin:
    """`subgroup_index` field to track index of operation in group

    :param subgroup_index:
    """

    def __post_init_post_parse__(self) -> None:
        self._subgroup_index: int | None = None

    @property
    def subgroup_index(self) -> int:
        if self._subgroup_index is None:
            raise ConfigInitializationException
        return self._subgroup_index

    @subgroup_index.setter
    def subgroup_index(self, value: int) -> None:
        self._subgroup_index = value


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
        return f'{package}.types.{module_name}.tezos_storage', storage_cls

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

        return f'{package}.types.{module_name}.tezos_parameters.{parameter_module}', parameter_cls

    @classmethod
    def format_untyped_operation_import(cls) -> tuple[str, str]:
        return 'dipdup.models.tezos_tzkt', 'TzktOperationData'

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
            return arg_name, f'TzktOrigination[{storage_cls}] | None'
        return arg_name, f'TzktOrigination[{storage_cls}]'

    @classmethod
    def format_operation_argument(
        cls,
        module_name: str,
        entrypoint: str,
        optional: bool,
        alias: str | None,
    ) -> tuple[str, str]:
        arg_name = alias or entrypoint
        entrypoint = entrypoint.lstrip('_')
        parameter_cls = f'{snake_to_pascal(arg_name)}Parameter'
        storage_cls = f'{snake_to_pascal(module_name)}Storage'
        if optional:
            return pascal_to_snake(arg_name), f'TzktTransaction[{parameter_cls}, {storage_cls}] | None'
        return pascal_to_snake(arg_name), f'TzktTransaction[{parameter_cls}, {storage_cls}]'

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
            return arg_name, 'TzktOperationData | None'
        return arg_name, 'TzktOperationData'


@dataclass
class OperationsHandlerTransactionPatternConfig(PatternConfig, SubgroupIndexMixin):
    """Operation handler pattern config

    :param type: always 'transaction'
    :param source: Match operations by source contract alias
    :param destination: Match operations by destination contract alias
    :param entrypoint: Match operations by contract entrypoint
    :param optional: Whether can operation be missing in operation group
    :param alias: Alias for operation (helps to avoid duplicates)
    """

    type: Literal['transaction'] = 'transaction'
    source: TezosContractConfig | None = None
    destination: TezosContractConfig | None = None
    entrypoint: str | None = None
    optional: bool = False
    alias: str | None = None

    def __post_init_post_parse__(self) -> None:
        SubgroupIndexMixin.__post_init_post_parse__(self)

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        if self.typed_contract:
            module_name = self.typed_contract.module_name
            yield 'dipdup.models.tezos_tzkt', 'TzktTransaction'
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
    def typed_contract(self) -> TezosContractConfig | None:
        if self.entrypoint and self.destination:
            return self.destination
        return None


@dataclass
class OperationsHandlerOriginationPatternConfig(PatternConfig, SubgroupIndexMixin):
    """Origination handler pattern config

    :param type: always 'origination'
    :param source: Match operations by source contract alias
    :param originated_contract: Match origination of exact contract
    :param optional: Whether can operation be missing in operation group
    :param strict: Match operations by storage only or by the whole code
    :param alias: Alias for operation (helps to avoid duplicates)
    """

    type: Literal['origination'] = 'origination'
    source: TezosContractConfig | None = None
    originated_contract: TezosContractConfig | None = None
    optional: bool = False
    strict: bool = False
    alias: str | None = None

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        if self.typed_contract:
            module_name = self.typed_contract.module_name
            yield 'dipdup.models.tezos_tzkt', 'TzktOrigination'
            yield self.format_storage_import(package, module_name)
        else:
            yield 'dipdup.models.tezos_tzkt', 'TzktOperationData'

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
    def typed_contract(self) -> TezosContractConfig | None:
        if self.originated_contract:
            return self.originated_contract
        return None


@dataclass
class OperationsHandlerSmartRollupExecutePatternConfig(PatternConfig, SubgroupIndexMixin):
    """Operation handler pattern config

    :param type: always 'sr_execute'
    :param source: Match operations by source contract alias
    :param destination: Match operations by destination contract alias
    :param optional: Whether can operation be missing in operation group
    :param alias: Alias for operation (helps to avoid duplicates)
    """

    type: Literal['sr_execute'] = 'sr_execute'
    source: TezosContractConfig | None = None
    destination: TezosContractConfig | None = None
    optional: bool = False
    alias: str | None = None

    def __post_init_post_parse__(self) -> None:
        SubgroupIndexMixin.__post_init_post_parse__(self)

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.models.tezos_tzkt', 'TzktSmartRollupExecute'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        arg_name = pascal_to_snake(self.alias or f'sr_execute_{self.subgroup_index}')
        if self.optional:
            yield arg_name, 'TzktSmartRollupExecute | None'
        else:
            yield arg_name, 'TzktSmartRollupExecute'

    @property
    def typed_contract(self) -> TezosContractConfig | None:
        if self.destination:
            return self.destination
        return None


@dataclass
class TzktOperationsIndexConfig(TzktIndexConfig):
    """Operation index config

    :param kind: always `tezos.tzkt.operations`
    :param datasource: Alias of index datasource in `datasources` section
    :param handlers: List of indexer handlers
    :param types: Types of transaction to fetch
    :param contracts: Aliases of contracts being indexed in `contracts` section
    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing at
    """

    kind: Literal['tezos.tzkt.operations']
    datasource: TzktDatasourceConfig
    handlers: tuple[TzktOperationsHandlerConfig, ...]
    contracts: list[TezosContractConfig] = field(default_factory=list)
    types: tuple[TzktOperationType, ...] = (TzktOperationType.transaction,)

    first_level: int = 0
    last_level: int = 0

    def get_subscriptions(self) -> set[Subscription]:
        subs = super().get_subscriptions()

        if TzktOperationType.transaction in self.types:
            if self.datasource.merge_subscriptions:
                subs.add(TransactionSubscription())
            else:
                for contract_config in self.contracts:
                    if not isinstance(contract_config, TezosContractConfig):
                        raise ConfigInitializationException
                    subs.add(TransactionSubscription(address=contract_config.address))

        if TzktOperationType.origination in self.types:
            subs.add(OriginationSubscription())

        if TzktOperationType.sr_execute in self.types:
            if self.datasource.merge_subscriptions:
                subs.add(SmartRollupExecuteSubscription())
            else:
                for contract_config in self.contracts:
                    if not isinstance(contract_config, TezosContractConfig):
                        raise ConfigInitializationException
                    if contract_config.address and contract_config.address.startswith('sr1'):
                        subs.add(SmartRollupExecuteSubscription(address=contract_config.address))

        return subs

    @classmethod
    def strip(cls, config_dict: dict[str, Any]) -> None:
        super().strip(config_dict)
        for handler in config_dict['handlers']:
            for item in handler['pattern']:
                item.pop('alias', None)


OperationsHandlerPatternConfigU = (
    OperationsHandlerTransactionPatternConfig
    | OperationsHandlerOriginationPatternConfig
    | OperationsHandlerSmartRollupExecutePatternConfig
)


@dataclass
class TzktOperationsHandlerConfig(HandlerConfig):
    """Operation handler config

    :param callback: Callback name
    :param pattern: Filters to match operation groups
    """

    pattern: tuple[OperationsHandlerPatternConfigU, ...]

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
                    (
                        'Pattern item is not unique. Set `alias` field to avoid duplicates.\n\n              handler:'
                        f' `{self.callback}`\n              entrypoint: `{arg}`'
                    ),
                )
            arg_names.add(arg)
            yield arg, arg_type


@dataclass
class OperationUnfilteredHandlerConfig(HandlerConfig):
    """Handler of unfiltered operation index

    :param callback: Callback name
    """

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.tezos_tzkt', 'TzktOperationData'
        yield package, 'models as models'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield 'operation', 'TzktOperationData'


@dataclass
class TzktOperationsUnfilteredIndexConfig(TzktIndexConfig):
    """Operation index config

    :param kind: always `tezos.tzkt.operations_unfiltered`
    :param datasource: Alias of index datasource in `datasources` section
    :param callback: Callback name
    :param types: Types of transaction to fetch

    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing at
    """

    kind: Literal['tezos.tzkt.operations_unfiltered']
    datasource: TzktDatasourceConfig
    callback: str
    types: tuple[TzktOperationType, ...] = (TzktOperationType.transaction,)

    first_level: int = 0
    last_level: int = 0

    def __post_init_post_parse__(self) -> None:
        super().__post_init_post_parse__()
        self.handler_config = OperationUnfilteredHandlerConfig(callback=self.callback)

    def get_subscriptions(self) -> set[Subscription]:
        subs = super().get_subscriptions()
        subs.add(TransactionSubscription())
        return subs


TzktOperationsHandlerConfigU = TzktOperationsHandlerConfig | OperationUnfilteredHandlerConfig
TzktOperationsIndexConfigU = TzktOperationsIndexConfig | TzktOperationsUnfilteredIndexConfig
