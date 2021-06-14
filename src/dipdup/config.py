import hashlib
import importlib
import json
import logging.config
import os
import re
import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import Enum
from os import environ as env
from os.path import dirname
from typing import Any, Callable, Dict, List, Optional, Sequence, Type, Union, cast
from urllib.parse import urlparse

from pydantic import Field, validator
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder
from ruamel.yaml import YAML
from typing_extensions import Literal

from dipdup.exceptions import ConfigurationError, HandlerImportError
from dipdup.utils import pascal_to_snake, snake_to_pascal

ROLLBACK_HANDLER = 'on_rollback'
CONFIGURE_HANDLER = 'on_configure'
BLOCK_HANDLER = 'on_block'
ENV_VARIABLE_REGEX = r'\${([\w]*):-(.*)}'

sys.path.append(os.getcwd())
_logger = logging.getLogger(__name__)


class OperationType(Enum):
    transaction = 'transaction'
    origination = 'origination'


@dataclass
class SqliteDatabaseConfig:
    """
    SQLite connection config

    :param path: Path to .sqlite3 file, leave default for in-memory database
    """

    kind: Literal['sqlite']
    path: str = ':memory:'

    @property
    def connection_string(self) -> str:
        return f'{self.kind}://{self.path}'


@dataclass
class MySQLDatabaseConfig:
    """MySQL database connection config

    :param host: Host
    :param port: Port
    :param user: User
    :param password: Password
    :param database: Database name
    """

    kind: Literal['mysql']
    host: str
    port: int
    user: str
    database: str
    password: str = ''

    @property
    def connection_string(self) -> str:
        return f'{self.kind}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}'


@dataclass
class PostgresDatabaseConfig:
    """Postgres database connection config

    :param host: Host
    :param port: Port
    :param user: User
    :param password: Password
    :param database: Database name
    :param schema_name: Schema name
    """

    kind: Literal['postgres']
    host: str
    port: int
    user: str
    database: str
    schema_name: str = 'public'
    password: str = ''

    @property
    def connection_string(self) -> str:
        return f'{self.kind}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?schema={self.schema_name}'


@dataclass
class ContractConfig:
    """Contract config

    :param network: Corresponding network alias, only for sanity checks
    :param address: Contract address
    :param typename: User-defined alias for the contract script
    """

    address: str
    typename: Optional[str] = None

    def __hash__(self):
        return hash(f'{self.address}{self.typename or ""}')

    @property
    def module_name(self) -> str:
        return self.typename if self.typename is not None else self.address

    @validator('address', allow_reuse=True)
    def valid_address(cls, v):
        # NOTE: Wallet addresses are allowed for debugging purposes (source field). Do we need a separate section?
        if not (v.startswith('KT1') or v.startswith('tz1')) or len(v) != 36:
            raise ConfigurationError(f'`{v}` is not a valid contract address')
        return v


@dataclass
class NameMixin:
    def __post_init_post_parse__(self) -> None:
        self._name: Optional[str] = None

    @property
    def name(self) -> str:
        if self._name is None:
            raise RuntimeError('Config is not pre-initialized')
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        self._name = name


@dataclass
class TzktDatasourceConfig(NameMixin):
    """TzKT datasource config

    :param url: Base API url
    """

    kind: Literal['tzkt']
    url: str

    def __hash__(self):
        return hash(self.url)

    @validator('url', allow_reuse=True)
    def valid_url(cls, v):
        parsed_url = urlparse(v)
        if not (parsed_url.scheme and parsed_url.netloc):
            raise ConfigurationError(f'`{v}` is not a valid datasource URL')
        return v


@dataclass
class BcdDatasourceConfig(NameMixin):
    """BCD datasource config

    :param url: Base API url
    """

    kind: Literal['bcd']
    url: str
    network: str

    def __hash__(self):
        return hash(self.url + self.network)

    @validator('url', allow_reuse=True)
    def valid_url(cls, v):
        parsed_url = urlparse(v)
        if not (parsed_url.scheme and parsed_url.netloc):
            raise ConfigurationError(f'`{v}` is not a valid datasource URL')
        return v


DatasourceConfigT = Union[TzktDatasourceConfig, BcdDatasourceConfig]


@dataclass
class PatternConfig(ABC):
    """Base for pattern config classes containing methods required for codegen"""

    @abstractmethod
    def get_handler_imports(self, package: str) -> str:
        ...

    @abstractmethod
    def get_handler_argument(self) -> str:
        ...

    @classmethod
    def format_storage_import(cls, package: str, module_name: str) -> str:
        storage_cls = f'{snake_to_pascal(module_name)}Storage'
        return f'from {package}.types.{module_name}.storage import {storage_cls}'

    @classmethod
    def format_parameter_import(cls, package: str, module_name: str, entrypoint: str) -> str:
        parameter_cls = f'{snake_to_pascal(entrypoint)}Parameter'
        return f'from {package}.types.{module_name}.parameter.{pascal_to_snake(entrypoint)} import {parameter_cls}'

    @classmethod
    def format_origination_argument(cls, module_name: str, optional: bool) -> str:
        storage_cls = f'{snake_to_pascal(module_name)}Storage'
        if optional:
            return f'{module_name}_origination: Optional[Origination[{storage_cls}]] = None,'
        return f'{module_name}_origination: Origination[{storage_cls}],'

    @classmethod
    def format_operation_argument(cls, module_name: str, entrypoint: str, optional: bool) -> str:
        parameter_cls = f'{snake_to_pascal(entrypoint)}Parameter'
        storage_cls = f'{snake_to_pascal(module_name)}Storage'
        if optional:
            return f'{entrypoint}: Optional[Transaction[{parameter_cls}, {storage_cls}]] = None,'
        return f'{entrypoint}: Transaction[{parameter_cls}, {storage_cls}],'

    @classmethod
    def format_empty_operation_argument(cls, transaction_id: int, optional: bool) -> str:
        if optional:
            return f'transaction_{transaction_id}: Optional[OperationData] = None,'
        return f'transaction_{transaction_id}: OperationData,'


@dataclass
class StorageTypeMixin:
    """`storage_type_cls` field"""

    def __post_init_post_parse__(self):
        self._storage_type_cls = None

    @property
    def storage_type_cls(self) -> Type:
        if self._storage_type_cls is None:
            raise RuntimeError('Config is not initialized')
        return self._storage_type_cls

    @storage_type_cls.setter
    def storage_type_cls(self, typ: Type) -> None:
        self._storage_type_cls = typ

    def initialize_storage_cls(self, package: str, module_name: str) -> None:
        _logger.info('Registering `%s` storage type', module_name)
        storage_type_module = importlib.import_module(f'{package}.types.{module_name}.storage')
        storage_type_cls = getattr(
            storage_type_module,
            snake_to_pascal(module_name) + 'Storage',
        )
        self.storage_type_cls = storage_type_cls


@dataclass
class ParameterTypeMixin:
    """`parameter_type_cls` field"""

    def __post_init_post_parse__(self):
        self._parameter_type_cls = None

    @property
    def parameter_type_cls(self) -> Type:
        if self._parameter_type_cls is None:
            raise RuntimeError('Config is not initialized')
        return self._parameter_type_cls

    @parameter_type_cls.setter
    def parameter_type_cls(self, typ: Type) -> None:
        self._parameter_type_cls = typ

    def initialize_parameter_cls(self, package: str, module_name: str, entrypoint: str) -> None:
        _logger.info('Registering parameter type for entrypoint `%s`', entrypoint)
        parameter_type_module = importlib.import_module(f'{package}.types.{module_name}.parameter.{pascal_to_snake(entrypoint)}')
        parameter_type_cls = getattr(parameter_type_module, snake_to_pascal(entrypoint) + 'Parameter')
        self.parameter_type_cls = parameter_type_cls


@dataclass
class TransactionIdMixin:
    """`transaction_id` field"""

    def __post_init_post_parse__(self):
        self._transaction_id = None

    @property
    def transaction_id(self) -> int:
        if self._transaction_id is None:
            raise RuntimeError('Config is not initialized')
        return self._transaction_id

    @transaction_id.setter
    def transaction_id(self, id_: int) -> None:
        self._transaction_id = id_


@dataclass
class OperationHandlerTransactionPatternConfig(PatternConfig, StorageTypeMixin, ParameterTypeMixin, TransactionIdMixin):
    """Operation handler pattern config

    :param destination: Alias of the contract to match
    :param entrypoint: Contract entrypoint
    """

    type: Literal['transaction'] = 'transaction'
    source: Optional[Union[str, ContractConfig]] = None
    destination: Optional[Union[str, ContractConfig]] = None
    entrypoint: Optional[str] = None
    optional: bool = False

    def __post_init_post_parse__(self):
        StorageTypeMixin.__post_init_post_parse__(self)
        ParameterTypeMixin.__post_init_post_parse__(self)
        TransactionIdMixin.__post_init_post_parse__(self)
        if self.entrypoint and not self.destination:
            raise ConfigurationError('Transactions with entrypoint must also have destination')

    def get_handler_imports(self, package: str) -> str:
        if not self.entrypoint:
            return ''

        module_name = self.destination_contract_config.module_name
        result = [
            self.format_parameter_import(package, module_name, self.entrypoint),
            self.format_storage_import(package, module_name),
        ]
        return '\n'.join(result)

    def get_handler_argument(self) -> str:
        if not self.entrypoint:
            return self.format_empty_operation_argument(self.transaction_id, self.optional)

        module_name = self.destination_contract_config.module_name
        return self.format_operation_argument(module_name, self.entrypoint, self.optional)

    @property
    def source_contract_config(self) -> ContractConfig:
        if not isinstance(self.source, ContractConfig):
            raise RuntimeError('Config is not initialized')
        return self.source

    @property
    def destination_contract_config(self) -> ContractConfig:
        if not isinstance(self.destination, ContractConfig):
            raise RuntimeError('Config is not initialized')
        return self.destination


@dataclass
class OperationHandlerOriginationPatternConfig(PatternConfig, StorageTypeMixin):
    source: Optional[Union[str, ContractConfig]] = None
    similar_to: Optional[Union[str, ContractConfig]] = None
    originated_contract: Optional[Union[str, ContractConfig]] = None
    type: Literal['origination'] = 'origination'
    optional: bool = False
    strict: bool = False

    def __post_init_post_parse__(self):
        super().__post_init_post_parse__()
        self._matched_originations = []

    def origination_processed(self, address: str) -> bool:
        if address in self._matched_originations:
            return True
        self._matched_originations.append(address)
        return False

    def __hash__(self) -> int:
        return hash(
            ''.join(
                [
                    self.source_contract_config.address if self.source else '',
                    self.similar_to_contract_config.address if self.similar_to else '',
                    self.originated_contract_config.address if self.originated_contract else '',
                ]
            )
        )

    def get_handler_imports(self, package: str) -> str:
        result = []
        if self.source:
            module_name = self.source_contract_config.module_name
            result.append(self.format_storage_import(package, module_name))
        if self.similar_to:
            module_name = self.similar_to_contract_config.module_name
            result.append(self.format_storage_import(package, module_name))
        if self.originated_contract:
            module_name = self.originated_contract_config.module_name
            result.append(self.format_storage_import(package, module_name))
        return '\n'.join(result)

    def get_handler_argument(self) -> str:
        return self.format_origination_argument(self.module_name, self.optional)

    @property
    def module_name(self) -> str:
        return self.contract_config.module_name

    @property
    def contract_config(self) -> ContractConfig:
        if self.originated_contract:
            return self.originated_contract_config
        if self.similar_to:
            return self.similar_to_contract_config
        if self.source:
            return self.source_contract_config
        raise RuntimeError

    @property
    def source_contract_config(self) -> ContractConfig:
        if not isinstance(self.source, ContractConfig):
            raise RuntimeError('Config is not initialized')
        return self.source

    @property
    def similar_to_contract_config(self) -> ContractConfig:
        if not isinstance(self.similar_to, ContractConfig):
            raise RuntimeError('Config is not initialized')
        return self.similar_to

    @property
    def originated_contract_config(self) -> ContractConfig:
        if not isinstance(self.originated_contract, ContractConfig):
            raise RuntimeError('Config is not initialized')
        return self.originated_contract


@dataclass
class HandlerConfig:
    callback: str

    def __post_init_post_parse__(self):
        self._callback_fn = None

    @property
    def callback_fn(self) -> Callable:
        if self._callback_fn is None:
            raise RuntimeError('Config is not initialized')
        return self._callback_fn

    @callback_fn.setter
    def callback_fn(self, fn: Callable) -> None:
        self._callback_fn = fn


OperationHandlerPatternConfigT = Union[OperationHandlerOriginationPatternConfig, OperationHandlerTransactionPatternConfig]


@dataclass
class OperationHandlerConfig(HandlerConfig):
    """Operation handler config

    :param callback: Name of method in `handlers` package
    :param pattern: Filters to match operations in group
    """

    pattern: List[OperationHandlerPatternConfigT]


@dataclass
class TemplateValuesMixin:
    def __post_init_post_parse__(self) -> None:
        self._template_values: Optional[Dict[str, str]] = None

    @property
    def template_values(self) -> Optional[Dict[str, str]]:
        return self._template_values

    @template_values.setter
    def template_values(self, value: Dict[str, str]) -> None:
        self._template_values = value


@dataclass
class IndexConfig(TemplateValuesMixin, NameMixin):
    datasource: Union[str, TzktDatasourceConfig]

    def __post_init_post_parse__(self) -> None:
        TemplateValuesMixin.__post_init_post_parse__(self)
        NameMixin.__post_init_post_parse__(self)

    def hash(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self,
                default=pydantic_encoder,
            ).encode(),
        ).hexdigest()

    @property
    def datasource_config(self) -> TzktDatasourceConfig:
        if not isinstance(self.datasource, TzktDatasourceConfig):
            raise RuntimeError('Config is not initialized')
        return self.datasource


@dataclass
class OperationIndexConfig(IndexConfig):
    """Operation index config

    :param datasource: Alias of datasource in `datasources` block
    :param contract: Alias of contract to fetch operations for
    :param first_block: First block to process
    :param last_block: Last block to process
    :param handlers: List of indexer handlers
    """

    kind: Literal["operation"]
    handlers: List[OperationHandlerConfig]
    types: Optional[List[OperationType]] = None
    contracts: Optional[List[Union[str, ContractConfig]]] = None

    stateless: bool = False
    first_block: int = 0
    last_block: int = 0

    @property
    def contract_configs(self) -> List[ContractConfig]:
        if not self.contracts:
            return []
        for contract in self.contracts:
            if not isinstance(contract, ContractConfig):
                raise RuntimeError('Config is not initialized')
        return cast(List[ContractConfig], self.contracts)


# FIXME: Inherit PatternConfig, cleanup
@dataclass
class BigMapHandlerPatternConfig:
    contract: Union[str, ContractConfig]
    path: str

    def __post_init_post_parse__(self):
        self._key_type_cls = None
        self._value_type_cls = None

    @property
    def contract_config(self) -> ContractConfig:
        if not isinstance(self.contract, ContractConfig):
            raise RuntimeError('Config is not initialized')
        return self.contract

    @property
    def key_type_cls(self) -> Type:
        if self._key_type_cls is None:
            raise RuntimeError('Config is not initialized')
        return self._key_type_cls

    @key_type_cls.setter
    def key_type_cls(self, typ: Type) -> None:
        self._key_type_cls = typ

    @property
    def value_type_cls(self) -> Type:
        if self._value_type_cls is None:
            raise RuntimeError('Config is not initialized')
        return self._value_type_cls

    @value_type_cls.setter
    def value_type_cls(self, typ: Type) -> None:
        self._value_type_cls = typ


@dataclass
class BigMapHandlerConfig(HandlerConfig):
    pattern: List[BigMapHandlerPatternConfig]


@dataclass
class BigMapIndexConfig(IndexConfig):
    kind: Literal['big_map']
    datasource: Union[str, TzktDatasourceConfig]
    handlers: List[BigMapHandlerConfig]

    stateless: bool = False
    first_block: int = 0
    last_block: int = 0


@dataclass
class BlockHandlerConfig(HandlerConfig):
    pattern = None


@dataclass
class BlockIndexConfig(IndexConfig):
    """Stub, not implemented"""

    kind: Literal['block']
    datasource: Union[str, TzktDatasourceConfig]
    handlers: List[BlockHandlerConfig]

    stateless: bool = False
    first_block: int = 0
    last_block: int = 0


@dataclass
class StaticTemplateConfig:
    kind = 'template'
    template: str
    values: Dict[str, str]


IndexConfigT = Union[OperationIndexConfig, BigMapIndexConfig, BlockIndexConfig, StaticTemplateConfig]
IndexConfigTemplateT = Union[OperationIndexConfig, BigMapIndexConfig, BlockIndexConfig]
HandlerPatternConfigT = Union[
    OperationHandlerOriginationPatternConfig, OperationHandlerTransactionPatternConfig, BigMapHandlerPatternConfig
]


@dataclass
class HasuraConfig:
    url: str
    admin_secret: Optional[str] = None

    @validator('url', allow_reuse=True)
    def valid_url(cls, v):
        parsed_url = urlparse(v)
        if not (parsed_url.scheme and parsed_url.netloc):
            raise ConfigurationError(f'`{v}` is not a valid Hasura URL')
        return v


@dataclass
class ConfigurationConfig:
    interval: int = 60
    args: Dict[str, Any] = Field(default_factory=dict)


@dataclass
class DipDupConfig:
    """Main dapp config

    :param spec_version: Version of specification
    :param package: Name of dapp python package, existing or not
    :param contracts: Mapping of contract aliases and contract configs
    :param datasources: Mapping of datasource aliases and datasource configs
    :param indexes: Mapping of index aliases and index configs
    :param templates: Mapping of template aliases and index templates
    :param database: Database config
    :param hasura: Hasura config
    :param configuration: Dynamic configuration parameters
    """

    spec_version: str
    package: str
    datasources: Dict[str, Union[TzktDatasourceConfig, BcdDatasourceConfig]]
    contracts: Dict[str, ContractConfig] = Field(default_factory=dict)
    indexes: Dict[str, IndexConfigT] = Field(default_factory=dict)
    templates: Optional[Dict[str, IndexConfigTemplateT]] = None
    database: Union[SqliteDatabaseConfig, MySQLDatabaseConfig, PostgresDatabaseConfig] = SqliteDatabaseConfig(kind='sqlite')
    hasura: Optional[HasuraConfig] = None
    configuration: Optional[ConfigurationConfig] = None

    def __post_init_post_parse__(self):
        self._callback_patterns: Dict[str, List[Sequence[HandlerPatternConfigT]]] = defaultdict(list)
        self._pre_initialized = []
        self._initialized = []
        self.validate()

    def validate(self) -> None:
        if isinstance(self.database, SqliteDatabaseConfig) and self.hasura:
            raise ConfigurationError('SQLite DB engine is not supported by Hasura')

    def get_contract(self, name: str) -> ContractConfig:
        try:
            return self.contracts[name]
        except KeyError as e:
            raise ConfigurationError(f'Contract `{name}` not found in `contracts` config section') from e

    def get_datasource(self, name: str) -> DatasourceConfigT:
        try:
            return self.datasources[name]
        except KeyError as e:
            raise ConfigurationError(f'Datasource `{name}` not found in `datasources` config section') from e

    def get_template(self, name: str) -> IndexConfigTemplateT:
        if not self.templates:
            raise ConfigurationError('`templates` section is missing')
        try:
            return self.templates[name]
        except KeyError as e:
            raise ConfigurationError(f'Template `{name}` not found in `templates` config section') from e

    def get_tzkt_datasource(self, name: str) -> TzktDatasourceConfig:
        datasource = self.get_datasource(name)
        if not isinstance(datasource, TzktDatasourceConfig):
            raise ConfigurationError('`datasource` field must refer to TzKT datasource')
        return datasource

    def get_rollback_fn(self) -> Type:
        try:
            module = f'{self.package}.handlers.{ROLLBACK_HANDLER}'
            return getattr(importlib.import_module(module), ROLLBACK_HANDLER)
        except (ModuleNotFoundError, AttributeError) as e:
            raise HandlerImportError(f'Module `{module}` not found. Have you forgot to call `init`?') from e

    def get_configure_fn(self) -> Type:
        try:
            module = f'{self.package}.handlers.{CONFIGURE_HANDLER}'
            return getattr(importlib.import_module(module), CONFIGURE_HANDLER)
        except (ModuleNotFoundError, AttributeError) as e:
            raise HandlerImportError(f'Module `{module}` not found. Have you forgot to call `init`?') from e

    def resolve_static_templates(self) -> None:
        _logger.info('Substituting index templates')
        for index_name, index_config in self.indexes.items():
            if isinstance(index_config, StaticTemplateConfig):
                template = self.get_template(index_config.template)
                raw_template = json.dumps(template, default=pydantic_encoder)
                for key, value in index_config.values.items():
                    value_regex = r'<[ ]*' + key + r'[ ]*>'
                    raw_template = re.sub(value_regex, value, raw_template)
                json_template = json.loads(raw_template)
                new_index_config = template.__class__(**json_template)
                new_index_config.template_values = index_config.values
                self.indexes[index_name] = new_index_config

    def _pre_initialize_index(self, index_name: str, index_config: IndexConfigT) -> None:
        """Resolve contract and datasource configs by aliases"""
        if index_name in self._pre_initialized:
            return

        if isinstance(index_config, OperationIndexConfig):
            index_config.name = index_name
            if isinstance(index_config.datasource, str):
                index_config.datasource = self.get_tzkt_datasource(index_config.datasource)

            if index_config.contracts is not None:
                for i, contract in enumerate(index_config.contracts):
                    if isinstance(contract, str):
                        index_config.contracts[i] = self.get_contract(contract)

            transaction_id = 0
            for handler_config in index_config.handlers:
                self._callback_patterns[handler_config.callback].append(handler_config.pattern)
                for pattern_config in handler_config.pattern:
                    if isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
                        if isinstance(pattern_config.destination, str):
                            pattern_config.destination = self.get_contract(pattern_config.destination)
                        if isinstance(pattern_config.source, str):
                            pattern_config.source = self.get_contract(pattern_config.source)
                        if not pattern_config.entrypoint:
                            pattern_config.transaction_id = transaction_id
                            transaction_id += 1

                    elif isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
                        if isinstance(pattern_config.source, str):
                            pattern_config.source = self.get_contract(pattern_config.source)
                        if isinstance(pattern_config.similar_to, str):
                            pattern_config.similar_to = self.get_contract(pattern_config.similar_to)
                        if isinstance(pattern_config.originated_contract, str):
                            pattern_config.originated_contract = self.get_contract(pattern_config.originated_contract)

        elif isinstance(index_config, BigMapIndexConfig):
            index_config.name = index_name
            if isinstance(index_config.datasource, str):
                index_config.datasource = self.get_tzkt_datasource(index_config.datasource)

            for handler in index_config.handlers:
                self._callback_patterns[handler.callback].append(handler.pattern)
                for pattern in handler.pattern:
                    if isinstance(pattern.contract, str):
                        pattern.contract = self.get_contract(pattern.contract)

        else:
            raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

        self._pre_initialized.append(index_name)

    def _pre_initialize(self) -> None:
        for name, config in self.datasources.items():
            config.name = name

        self.resolve_static_templates()
        for index_name, index_config in self.indexes.items():
            self._pre_initialize_index(index_name, index_config)

        _logger.info('Verifying callback uniqueness')
        for callback, patterns in self._callback_patterns.items():
            if len(patterns) > 1:

                def get_pattern_type(pattern: Sequence[HandlerPatternConfigT]) -> str:
                    module_names = []
                    for pattern_config in pattern:
                        if isinstance(pattern_config, OperationHandlerTransactionPatternConfig) and pattern_config.entrypoint:
                            module_names.append(pattern_config.destination_contract_config.module_name)
                        elif isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
                            module_names.append(pattern_config.module_name)
                        # TODO: Check BigMapHandlerPatternConfig
                    return '::'.join(module_names)

                pattern_types = list(map(get_pattern_type, patterns))
                if any(map(lambda x: x != pattern_types[0], pattern_types)):
                    _logger.warning(
                        'Callback `%s` used multiple times with different signatures. Make sure you have specified contract typenames',
                        callback,
                    )

    @property
    def package_path(self) -> str:
        package = importlib.import_module(self.package)
        return dirname(package.__file__)

    @property
    def cache_enabled(self) -> bool:
        return isinstance(self.database, SqliteDatabaseConfig)

    @classmethod
    def load(
        cls,
        filenames: List[str],
    ) -> 'DipDupConfig':

        current_workdir = os.path.join(os.getcwd())

        json_config: Dict[str, Any] = {}
        for filename in filenames:
            filename = os.path.join(current_workdir, filename)

            _logger.info('Loading config from %s', filename)
            with open(filename) as file:
                raw_config = file.read()

            _logger.info('Substituting environment variables')
            for match in re.finditer(ENV_VARIABLE_REGEX, raw_config):
                variable, default_value = match.group(1), match.group(2)
                value = env.get(variable)
                if not default_value and not value:
                    raise ConfigurationError(f'Environment variable `{variable}` is not set')
                placeholder = '${' + variable + ':-' + default_value + '}'
                raw_config = raw_config.replace(placeholder, value or default_value)

            json_config = {
                **json_config,
                **YAML(typ='base').load(raw_config),
            }

        config = cls(**json_config)
        return config

    def _initialize_handler_callback(self, handler_config: HandlerConfig) -> None:
        _logger.info('Registering handler callback `%s`', handler_config.callback)
        try:
            handler_module = importlib.import_module(f'{self.package}.handlers.{handler_config.callback}')
            callback_fn = getattr(handler_module, handler_config.callback)
            handler_config.callback_fn = callback_fn
        except ImportError as e:
            if 'Context' in str(e):
                _logger.warning('Found broken imports, attemping to fix them')
                raise HandlerImportError from e
            raise

    def initialize_index(self, index_name: str, index_config: IndexConfigT) -> None:
        if index_name in self._initialized:
            return

        if isinstance(index_config, StaticTemplateConfig):
            raise RuntimeError('Config is not pre-initialized')

        if isinstance(index_config, OperationIndexConfig):

            for operation_handler_config in index_config.handlers:
                self._initialize_handler_callback(operation_handler_config)

                for operation_pattern_config in operation_handler_config.pattern:
                    if isinstance(operation_pattern_config, OperationHandlerTransactionPatternConfig):
                        if operation_pattern_config.entrypoint:
                            module_name = operation_pattern_config.destination_contract_config.module_name
                            operation_pattern_config.initialize_parameter_cls(
                                self.package, module_name, operation_pattern_config.entrypoint
                            )
                            operation_pattern_config.initialize_storage_cls(self.package, module_name)
                    elif isinstance(operation_pattern_config, OperationHandlerOriginationPatternConfig):
                        module_name = operation_pattern_config.module_name
                        operation_pattern_config.initialize_storage_cls(self.package, module_name)
                    else:
                        raise NotImplementedError

        # TODO: BigMapTypeMixin, initialize_big_map_type
        elif isinstance(index_config, BigMapIndexConfig):
            for big_map_handler_config in index_config.handlers:
                self._initialize_handler_callback(big_map_handler_config)

                for big_map_pattern_config in big_map_handler_config.pattern:
                    _logger.info('Registering big map types for path `%s`', big_map_pattern_config.path)
                    key_type_module = importlib.import_module(
                        f'{self.package}'
                        f'.types'
                        f'.{big_map_pattern_config.contract_config.module_name}'
                        f'.big_map'
                        f'.{pascal_to_snake(big_map_pattern_config.path)}_key'
                    )
                    key_type_cls = getattr(key_type_module, snake_to_pascal(big_map_pattern_config.path + '_key'))
                    big_map_pattern_config.key_type_cls = key_type_cls

                    value_type_module = importlib.import_module(
                        f'{self.package}'
                        f'.types'
                        f'.{big_map_pattern_config.contract_config.module_name}'
                        f'.big_map'
                        f'.{pascal_to_snake(big_map_pattern_config.path)}_value'
                    )
                    value_type_cls = getattr(value_type_module, snake_to_pascal(big_map_pattern_config.path + '_value'))
                    big_map_pattern_config.value_type_cls = value_type_cls

        else:
            raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

        self._initialized.append(index_name)

    def initialize(self) -> None:
        _logger.info('Setting up handlers and types for package `%s`', self.package)

        self._pre_initialize()
        for index_name, index_config in self.indexes.items():
            self.initialize_index(index_name, index_config)


@dataclass
class LoggingConfig:
    config: Dict[str, Any]

    @classmethod
    def load(
        cls,
        filename: str,
    ) -> 'LoggingConfig':

        current_workdir = os.path.join(os.getcwd())
        filename = os.path.join(current_workdir, filename)

        with open(filename) as file:
            return cls(config=YAML().load(file.read()))

    def apply(self):
        logging.config.dictConfig(self.config)
