import hashlib
import importlib
import json
import logging.config
import operator
import os
import re
import sys
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from contextlib import suppress
from copy import copy
from dataclasses import field
from enum import Enum
from functools import reduce
from os import environ as env
from os.path import dirname
from pydoc import locate
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, Sequence, Set, Tuple, Type, TypeVar, Union, cast
from urllib.parse import urlparse

from pydantic import Field, validator
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder
from ruamel.yaml import YAML
from typing_extensions import Literal

from dipdup.exceptions import ConfigInitializationException, ConfigurationError
from dipdup.utils import import_from, pascal_to_snake, snake_to_pascal

ENV_VARIABLE_REGEX = r'\${([\w]*):-(.*)}'
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_SLEEP = 1

sys.path.append(os.getcwd())
_logger = logging.getLogger('dipdup.config')


class OperationType(Enum):
    transaction = 'transaction'
    origination = 'origination'
    migration = 'migration'


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
class PostgresDatabaseConfig:
    """Postgres database connection config

    :param host: Host
    :param port: Port
    :param user: User
    :param password: Password
    :param database: Database name
    :param schema_name: Schema name
    :param immune_tables: List of tables to preserve during reindexing
    """

    kind: Literal['postgres']
    host: str
    user: str = 'postgres'
    database: str = 'postgres'
    port: int = 5432
    schema_name: str = 'public'
    password: str = ''
    immune_tables: List[str] = Field(default_factory=list)
    connection_timeout: int = 60

    @property
    def connection_string(self) -> str:
        # NOTE: `maxsize=1` is important! Concurrency will be broken otherwise.
        # NOTE: https://github.com/tortoise/tortoise-orm/issues/792
        return f'{self.kind}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?schema={self.schema_name}&maxsize=1'

    @validator('immune_tables')
    def valid_immune_tables(cls, v):
        for table in v:
            if table.startswith('dipdup'):
                raise ConfigurationError('Tables with `dipdup` prefix can\'t be immune')
        return v


@dataclass
class HTTPConfig:
    cache: Optional[bool] = None
    retry_count: Optional[int] = None
    retry_sleep: Optional[float] = None
    retry_multiplier: Optional[float] = None
    ratelimit_rate: Optional[int] = None
    ratelimit_period: Optional[int] = None
    connection_limit: Optional[int] = None  # default 100
    connection_timeout: Optional[int] = None  # default 60
    batch_size: Optional[int] = None

    def merge(self, other: Optional['HTTPConfig']) -> 'HTTPConfig':
        config = copy(self)
        if other:
            for k, v in other.__dict__.items():
                if v is not None:
                    setattr(config, k, v)
        return config


@dataclass
class NameMixin:
    def __post_init_post_parse__(self) -> None:
        self._name: Optional[str] = None

    @property
    def name(self) -> str:
        if self._name is None:
            raise ConfigInitializationException
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        self._name = name


@dataclass
class ContractConfig(NameMixin):
    """Contract config

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
        if not (v.startswith('KT') or v.startswith('tz')) or len(v) != 36:
            raise ConfigurationError(f'`{v}` is not a valid contract address')
        return v


@dataclass
class TzktDatasourceConfig(NameMixin):
    """TzKT datasource config

    :param url: Base API url
    """

    kind: Literal['tzkt']
    url: str
    http: Optional[HTTPConfig] = None

    def __hash__(self):
        return hash(self.url)

    def __post_init_post_parse__(self) -> None:
        super().__post_init_post_parse__()
        if self.http and self.http.batch_size and self.http.batch_size > 10000:
            raise ConfigurationError('`batch_size` must be less than 10000')
        parsed_url = urlparse(self.url)
        if not (parsed_url.scheme and parsed_url.netloc):
            raise ConfigurationError(f'`{self.url}` is not a valid datasource URL')


@dataclass
class BcdDatasourceConfig(NameMixin):
    """BCD datasource config

    :param url: Base API url
    """

    kind: Literal['bcd']
    url: str
    network: str
    http: Optional[HTTPConfig] = None

    def __hash__(self):
        return hash(self.url + self.network)

    @validator('url', allow_reuse=True)
    def valid_url(cls, v):
        parsed_url = urlparse(v)
        if not (parsed_url.scheme and parsed_url.netloc):
            raise ConfigurationError(f'`{v}` is not a valid datasource URL')
        return v


@dataclass
class CoinbaseDatasourceConfig(NameMixin):
    kind: Literal['coinbase']
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    passphrase: Optional[str] = None
    http: Optional[HTTPConfig] = None

    def __hash__(self):
        return hash(self.kind)


DatasourceConfigT = Union[TzktDatasourceConfig, BcdDatasourceConfig, CoinbaseDatasourceConfig]


@dataclass
class CodegenMixin(ABC):
    """Base for pattern config classes containing methods required for codegen"""

    @abstractmethod
    def iter_imports(self, package: str) -> Iterator[Tuple[str, str]]:
        ...

    @abstractmethod
    def iter_arguments(self) -> Iterator[Tuple[str, str]]:
        ...

    def format_imports(self, package: str) -> Iterator[str]:
        for package, cls in self.iter_imports(package):
            yield f'from {package} import {cls}'

    def format_arguments(self) -> Iterator[str]:
        arguments = list(self.iter_arguments())
        i, counter = 0, Counter(name for name, _ in arguments)

        for name, cls in arguments:
            if counter[name] > 1:
                yield f'{name}_{i}: {cls}'
                i += 1
            else:
                yield f'{name}: {cls}'

    def locate_arguments(self) -> Dict[str, Optional[Type]]:
        kwargs: Dict[str, Optional[Type]] = {}
        for name, cls in self.iter_arguments():
            cls = cls.split(' as ')[0]
            kwargs[name] = cast(Optional[Type], locate(cls))
        return kwargs


class PatternConfig(CodegenMixin, ABC):
    @classmethod
    def format_storage_import(cls, package: str, module_name: str) -> Tuple[str, str]:
        storage_cls = f'{snake_to_pascal(module_name)}Storage'
        return f'{package}.types.{module_name}.storage', storage_cls

    @classmethod
    def format_parameter_import(cls, package: str, module_name: str, entrypoint: str) -> Tuple[str, str]:
        entrypoint = entrypoint.lstrip('_')
        parameter_cls = f'{snake_to_pascal(entrypoint)}Parameter'
        return f'{package}.types.{module_name}.parameter.{pascal_to_snake(entrypoint)}', parameter_cls

    @classmethod
    def format_origination_argument(cls, module_name: str, optional: bool) -> Tuple[str, str]:
        storage_cls = f'{snake_to_pascal(module_name)}Storage'
        if optional:
            return f'{module_name}_origination', f'Optional[Origination[{storage_cls}]] = None'
        return f'{module_name}_origination', f'Origination[{storage_cls}]'

    @classmethod
    def format_operation_argument(cls, module_name: str, entrypoint: str, optional: bool) -> Tuple[str, str]:
        entrypoint = entrypoint.lstrip('_')
        parameter_cls = f'{snake_to_pascal(entrypoint)}Parameter'
        storage_cls = f'{snake_to_pascal(module_name)}Storage'
        if optional:
            return pascal_to_snake(entrypoint), f'Optional[Transaction[{parameter_cls}, {storage_cls}]] = None'
        return pascal_to_snake(entrypoint), f'Transaction[{parameter_cls}, {storage_cls}]'

    @classmethod
    def format_empty_operation_argument(cls, transaction_id: int, optional: bool) -> Tuple[str, str]:
        if optional:
            return f'transaction_{transaction_id}', 'Optional[OperationData] = None'
        return f'transaction_{transaction_id}', 'OperationData'


@dataclass
class StorageTypeMixin:
    """`storage_type_cls` field"""

    def __post_init_post_parse__(self):
        self._storage_type_cls = None

    @property
    def storage_type_cls(self) -> Type:
        if self._storage_type_cls is None:
            raise ConfigInitializationException
        return self._storage_type_cls

    @storage_type_cls.setter
    def storage_type_cls(self, typ: Type) -> None:
        self._storage_type_cls = typ

    def initialize_storage_cls(self, package: str, module_name: str) -> None:
        _logger.debug('Registering `%s` storage type', module_name)
        cls_name = snake_to_pascal(module_name) + 'Storage'
        module_name = f'{package}.types.{module_name}.storage'
        self.storage_type_cls = import_from(module_name, cls_name)


T = TypeVar('T')


@dataclass
class ParentMixin(Generic[T]):
    """`parent` field for index and template configs"""

    def __post_init_post_parse__(self: 'ParentMixin') -> None:
        self._parent: Optional[T] = None

    @property
    def parent(self) -> Optional[T]:
        return self._parent

    @parent.setter
    def parent(self, config: T) -> None:
        if self._parent and config is not self._parent:
            raise ConfigInitializationException
        self._parent = config


@dataclass
class ParameterTypeMixin:
    """`parameter_type_cls` field"""

    def __post_init_post_parse__(self):
        self._parameter_type_cls = None

    @property
    def parameter_type_cls(self) -> Type:
        if self._parameter_type_cls is None:
            raise ConfigInitializationException
        return self._parameter_type_cls

    @parameter_type_cls.setter
    def parameter_type_cls(self, typ: Type) -> None:
        self._parameter_type_cls = typ

    def initialize_parameter_cls(self, package: str, typename: str, entrypoint: str) -> None:
        _logger.debug('Registering parameter type for entrypoint `%s`', entrypoint)
        entrypoint = entrypoint.lstrip('_')
        module_name = f'{package}.types.{typename}.parameter.{pascal_to_snake(entrypoint)}'
        cls_name = snake_to_pascal(entrypoint) + 'Parameter'
        self.parameter_type_cls = import_from(module_name, cls_name)


@dataclass
class TransactionIdMixin:
    """`transaction_id` field"""

    def __post_init_post_parse__(self):
        self._transaction_id = None

    @property
    def transaction_id(self) -> int:
        if self._transaction_id is None:
            raise ConfigInitializationException
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

    def iter_imports(self, package: str) -> Iterator[Tuple[str, str]]:
        if not self.entrypoint:
            return

        module_name = self.destination_contract_config.module_name
        yield 'dipdup.models', 'Transaction'
        yield self.format_parameter_import(package, module_name, self.entrypoint)
        yield self.format_storage_import(package, module_name)

    def iter_arguments(self) -> Iterator[Tuple[str, str]]:
        if not self.entrypoint:
            yield self.format_empty_operation_argument(self.transaction_id, self.optional)
        else:
            module_name = self.destination_contract_config.module_name
            yield self.format_operation_argument(module_name, self.entrypoint, self.optional)

    @property
    def source_contract_config(self) -> ContractConfig:
        if not isinstance(self.source, ContractConfig):
            raise ConfigInitializationException
        return self.source

    @property
    def destination_contract_config(self) -> ContractConfig:
        if not isinstance(self.destination, ContractConfig):
            raise ConfigInitializationException
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

    def iter_imports(self, package: str) -> Iterator[Tuple[str, str]]:
        if self.source:
            module_name = self.source_contract_config.module_name
        elif self.similar_to:
            module_name = self.similar_to_contract_config.module_name
        elif self.originated_contract:
            module_name = self.originated_contract_config.module_name
        else:
            raise ConfigurationError('Origination pattern must have at least one of `source`, `similar_to`, `originated_contract` fields')
        yield 'dipdup.models', 'Origination'
        yield self.format_storage_import(package, module_name)

    def iter_arguments(self) -> Iterator[Tuple[str, str]]:
        yield self.format_origination_argument(self.module_name, self.optional)

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
            raise ConfigInitializationException
        return self.source

    @property
    def similar_to_contract_config(self) -> ContractConfig:
        if not isinstance(self.similar_to, ContractConfig):
            raise ConfigInitializationException
        return self.similar_to

    @property
    def originated_contract_config(self) -> ContractConfig:
        if not isinstance(self.originated_contract, ContractConfig):
            raise ConfigInitializationException
        return self.originated_contract


@dataclass
class CallbackMixin(CodegenMixin):
    callback: str

    def __init_subclass__(cls, kind: str):
        cls._kind = kind  # type: ignore

    def __post_init_post_parse__(self):
        self._callback_fn = None
        if self.callback and self.callback != pascal_to_snake(self.callback):
            raise ConfigurationError('`callback` field must conform to snake_case naming style')

    @property
    def kind(self) -> str:
        return self._kind  # type: ignore

    @property
    def callback_fn(self) -> Callable:
        if self._callback_fn is None:
            raise ConfigInitializationException
        return self._callback_fn

    @callback_fn.setter
    def callback_fn(self, fn: Callable) -> None:
        self._callback_fn = fn

    def initialize_callback_fn(self, package: str):
        if self._callback_fn:
            return
        _logger.debug('Registering %s callback `%s`', self.kind, self.callback)
        module_name = f'{package}.{self.kind}s.{self.callback}'
        fn_name = self.callback
        self.callback_fn = import_from(module_name, fn_name)


@dataclass
class HandlerConfig(CallbackMixin, ParentMixin['IndexConfig'], kind='handler'):
    def __post_init_post_parse__(self) -> None:
        CallbackMixin.__post_init_post_parse__(self)
        ParentMixin.__post_init_post_parse__(self)


OperationHandlerPatternConfigT = Union[OperationHandlerOriginationPatternConfig, OperationHandlerTransactionPatternConfig]


@dataclass
class OperationHandlerConfig(HandlerConfig, kind='handler'):
    """Operation handler config

    :param callback: Name of method in `handlers` package
    :param pattern: Filters to match operations in group
    """

    pattern: List[OperationHandlerPatternConfigT]

    def iter_imports(self, package: str) -> Iterator[Tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        for pattern in self.pattern:
            yield from pattern.iter_imports(package)

    def iter_arguments(self) -> Iterator[Tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        for pattern in self.pattern:
            yield from pattern.iter_arguments()


@dataclass
class TemplateValuesMixin:
    def __post_init_post_parse__(self) -> None:
        self._template_values: Dict[str, str] = {}

    @property
    def template_values(self) -> Dict[str, str]:
        return self._template_values

    @template_values.setter
    def template_values(self, value: Dict[str, str]) -> None:
        self._template_values = value


@dataclass
class IndexTemplateConfig(NameMixin):
    kind = 'template'
    template: str
    values: Dict[str, str]


@dataclass
class IndexConfig(TemplateValuesMixin, NameMixin, ParentMixin['ResolvedIndexConfigT']):
    datasource: Union[str, TzktDatasourceConfig]

    def __post_init_post_parse__(self) -> None:
        TemplateValuesMixin.__post_init_post_parse__(self)
        NameMixin.__post_init_post_parse__(self)
        ParentMixin.__post_init_post_parse__(self)

    def dumps(self) -> str:
        return json.dumps(self, default=pydantic_encoder)

    def json(self) -> Dict[str, Any]:
        return json.loads(self.dumps())

    def hash(self) -> str:
        config_json = self.dumps()
        config_hash = hashlib.sha256(config_json.encode()).hexdigest()
        return config_hash

    @property
    def datasource_config(self) -> TzktDatasourceConfig:
        if not isinstance(self.datasource, TzktDatasourceConfig):
            raise ConfigInitializationException
        return self.datasource


@dataclass
class OperationIndexConfig(IndexConfig):
    """Operation index config

    :param datasource: Alias of index datasource in `datasources` section
    :param contracts: Aliases of contracts being indexed in `contracts` section
    :param first_level: First block to process (use with `--oneshot` run argument)
    :param last_level: Last block to process (use with `--oneshot` run argument)
    :param handlers: List of indexer handlers
    """

    kind: Literal["operation"]
    handlers: List[OperationHandlerConfig]
    types: Optional[List[OperationType]] = None
    contracts: Optional[List[Union[str, ContractConfig]]] = None

    first_level: int = 0
    last_level: int = 0

    @property
    def contract_configs(self) -> List[ContractConfig]:
        if not self.contracts:
            return []
        for contract in self.contracts:
            if not isinstance(contract, ContractConfig):
                raise ConfigInitializationException
        return cast(List[ContractConfig], self.contracts)

    @property
    def entrypoints(self) -> Set[str]:
        entrypoints = set()
        for handler in self.handlers:
            for pattern in handler.pattern:
                if isinstance(pattern, OperationHandlerTransactionPatternConfig) and pattern.entrypoint:
                    entrypoints.add(pattern.entrypoint)
        return entrypoints


@dataclass
class BigMapHandlerConfig(HandlerConfig, kind='handler'):
    contract: Union[str, ContractConfig]
    path: str

    def __post_init_post_parse__(self):
        super().__post_init_post_parse__()
        self._key_type_cls = None
        self._value_type_cls = None

    @classmethod
    def format_key_import(cls, package: str, module_name: str, path: str) -> Tuple[str, str]:
        key_cls = f'{snake_to_pascal(module_name)}Key'
        key_module = f'{path}_key'
        return f'{package}.types.{module_name}.big_map.{key_module}', key_cls

    @classmethod
    def format_value_import(cls, package: str, module_name: str, path: str) -> Tuple[str, str]:
        value_cls = f'{snake_to_pascal(module_name)}Value'
        value_module = f'{path}_value'
        return f'{package}.types.{module_name}.big_map.{value_module}', value_cls

    @classmethod
    def format_big_map_diff_argument(cls, module_name: str) -> Tuple[str, str]:
        key_cls = f'{snake_to_pascal(module_name)}Key'
        value_cls = f'{snake_to_pascal(module_name)}Value'
        return module_name, f'BigMapDiff[{key_cls}, {value_cls}]'

    def iter_imports(self, package: str) -> Iterator[Tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models', 'BigMapDiff'
        yield package, 'models as models'

        yield self.format_key_import(package, self.contract_config.module_name, self.path)
        yield self.format_value_import(package, self.contract_config.module_name, self.path)

    def iter_arguments(self) -> Iterator[Tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield self.format_big_map_diff_argument(self.contract_config.module_name)

    @property
    def contract_config(self) -> ContractConfig:
        if not isinstance(self.contract, ContractConfig):
            raise ConfigInitializationException
        return self.contract

    @property
    def key_type_cls(self) -> Type:
        if self._key_type_cls is None:
            raise ConfigInitializationException
        return self._key_type_cls

    @key_type_cls.setter
    def key_type_cls(self, typ: Type) -> None:
        self._key_type_cls = typ

    @property
    def value_type_cls(self) -> Type:
        if self._value_type_cls is None:
            raise ConfigInitializationException
        return self._value_type_cls

    @value_type_cls.setter
    def value_type_cls(self, typ: Type) -> None:
        self._value_type_cls = typ

    def initialize_big_map_type(self, package: str) -> None:
        _logger.debug('Registering big map types for path `%s`', self.path)
        path = pascal_to_snake(self.path.replace('.', '_'))

        module_name = f'{package}.types.{self.contract_config.module_name}.big_map.{path}_key'
        cls_name = snake_to_pascal(path + '_key')
        self.key_type_cls = import_from(module_name, cls_name)

        module_name = f'{package}.types.{self.contract_config.module_name}.big_map.{path}_value'
        cls_name = snake_to_pascal(path + '_value')
        self.value_type_cls = import_from(module_name, cls_name)


@dataclass
class BigMapIndexConfig(IndexConfig):
    kind: Literal['big_map']
    datasource: Union[str, TzktDatasourceConfig]
    handlers: List[BigMapHandlerConfig]

    first_level: int = 0
    last_level: int = 0

    @property
    def contracts(self) -> List[ContractConfig]:
        return list(set([cast(ContractConfig, handler_config.contract) for handler_config in self.handlers]))


IndexConfigT = Union[OperationIndexConfig, BigMapIndexConfig, IndexTemplateConfig]
ResolvedIndexConfigT = Union[OperationIndexConfig, BigMapIndexConfig]
HandlerPatternConfigT = Union[OperationHandlerOriginationPatternConfig, OperationHandlerTransactionPatternConfig]


@dataclass
class HasuraConfig:
    url: str
    admin_secret: Optional[str] = None
    source: str = 'default'
    select_limit: int = 100
    allow_aggregations: bool = True
    camel_case: bool = False
    rest: bool = True
    http: Optional[HTTPConfig] = None

    @validator('url', allow_reuse=True)
    def valid_url(cls, v):
        parsed_url = urlparse(v)
        if not (parsed_url.scheme and parsed_url.netloc):
            raise ConfigurationError(f'`{v}` is not a valid Hasura URL')
        return v.rstrip('/')

    @validator('source', allow_reuse=True)
    def valid_source(cls, v):
        if v != 'default':
            raise NotImplementedError('Multiple Hasura sources are not supported at the moment')

    @property
    def headers(self) -> Dict[str, str]:
        if self.admin_secret:
            return {'X-Hasura-Admin-Secret': self.admin_secret}
        return {}


@dataclass
class JobConfig(NameMixin):
    hook: Union[str, 'HookConfig']
    crontab: Optional[str] = None
    interval: Optional[int] = None
    args: Dict[str, Any] = field(default_factory=dict)

    def __post_init_post_parse__(self):
        if int(bool(self.crontab)) + int(bool(self.interval)) != 1:
            raise ConfigurationError('Either `interval` or `crontab` field must be specified')
        NameMixin.__post_init_post_parse__(self)

    @property
    def hook_config(self) -> 'HookConfig':
        if not isinstance(self.hook, HookConfig):
            raise ConfigInitializationException
        return self.hook


@dataclass
class SentryConfig:
    dsn: str
    environment: Optional[str] = None
    debug: bool = False


@dataclass
class HookConfig(CallbackMixin, kind='hook'):
    args: Dict[str, str] = field(default_factory=dict)
    atomic: bool = False

    def iter_arguments(self) -> Iterator[Tuple[str, str]]:
        yield 'ctx', 'HookContext'
        for name, annotation in self.args.items():
            yield name, annotation.split('.')[-1]

    def iter_imports(self, package: str) -> Iterator[Tuple[str, str]]:
        yield 'dipdup.context', 'HookContext'
        for _, annotation in self.args.items():
            with suppress(ValueError):
                package, obj = annotation.rsplit('.', 1)
                yield package, obj

    @property
    def _args_with_context(self) -> Dict[str, str]:
        return {
            'ctx': 'dipdup.context.HookContext',
            **self.args,
        }


default_hooks = {
    # NOTE: After schema initialization. Default: nothing.
    'on_restart': HookConfig(
        callback='on_restart',
    ),
    # NOTE: On reorg message. Default: reindex.
    'on_rollback': HookConfig(
        callback='on_rollback',
        args=dict(
            datasource='dipdup.datasources.datasource.Datasource',
            from_level='int',
            to_level='int',
        ),
    ),
    # NOTE: After restart (important!) after ctx.reindex call. Default: nothing.
    'on_reindex': HookConfig(
        callback='on_reindex',
    ),
}


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
    :param jobs: Mapping of job aliases and job configs
    :param sentry: Sentry integration config
    """

    spec_version: str
    package: str
    datasources: Dict[str, DatasourceConfigT]
    database: Union[SqliteDatabaseConfig, PostgresDatabaseConfig] = SqliteDatabaseConfig(kind='sqlite')
    contracts: Dict[str, ContractConfig] = Field(default_factory=dict)
    indexes: Dict[str, IndexConfigT] = Field(default_factory=dict)
    templates: Dict[str, ResolvedIndexConfigT] = Field(default_factory=dict)
    jobs: Dict[str, JobConfig] = Field(default_factory=dict)
    hooks: Dict[str, HookConfig] = Field(default_factory=dict)
    hasura: Optional[HasuraConfig] = None
    sentry: Optional[SentryConfig] = None

    def __post_init_post_parse__(self):
        self._filenames: List[str] = []
        self._environment: Dict[str, str] = {}
        self._callback_patterns: Dict[str, List[Sequence[HandlerPatternConfigT]]] = defaultdict(list)
        self._default_hooks: bool = False
        self._links_resolved: Set[str] = set()
        self._imports_resolved: Set[str] = set()
        self._package_path: Optional[str] = None

    @property
    def environment(self) -> Dict[str, str]:
        return self._environment

    @property
    def filenames(self) -> List[str]:
        return self._filenames

    @property
    def package_path(self) -> str:
        if not self._package_path:
            package = importlib.import_module(self.package)
            self._package_path = dirname(package.__file__)

        return self._package_path

    @package_path.setter
    def package_path(self, value: str):
        if self._package_path:
            raise ConfigInitializationException
        self._package_path = value

    @classmethod
    def load(
        cls,
        filenames: List[str],
    ) -> 'DipDupConfig':

        current_workdir = os.path.join(os.getcwd())

        json_config: Dict[str, Any] = {}
        config_environment: Dict[str, str] = {}
        for filename in filenames:
            filename = os.path.join(current_workdir, filename)

            _logger.info('Loading config from %s', filename)
            with open(filename) as file:
                raw_config = file.read()

            _logger.info('Substituting environment variables')
            for match in re.finditer(ENV_VARIABLE_REGEX, raw_config):
                variable, default_value = match.group(1), match.group(2)
                config_environment[variable] = default_value
                value = env.get(variable)
                if not default_value and not value:
                    raise ConfigurationError(f'Environment variable `{variable}` is not set')
                placeholder = '${' + variable + ':-' + default_value + '}'
                raw_config = raw_config.replace(placeholder, value or default_value)

            json_config = {
                **json_config,
                **YAML(typ='base').load(raw_config),
            }

        try:
            config = cls(**json_config)
            config._environment = config_environment
            config._filenames = filenames
        except Exception as e:
            raise ConfigurationError(str(e)) from e
        return config

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

    def get_template(self, name: str) -> ResolvedIndexConfigT:
        try:
            return self.templates[name]
        except KeyError as e:
            raise ConfigurationError(f'Template `{name}` not found in `templates` config section') from e

    def get_hook(self, name: str) -> HookConfig:
        try:
            return self.hooks[name]
        except KeyError as e:
            raise ConfigurationError(f'Hook `{name}` not found in `templates` config section') from e

    def get_tzkt_datasource(self, name: str) -> TzktDatasourceConfig:
        datasource = self.get_datasource(name)
        if not isinstance(datasource, TzktDatasourceConfig):
            raise ConfigurationError('`datasource` field must refer to TzKT datasource')
        return datasource

    def initialize(self, skip_imports: bool = False) -> None:
        self._set_names()
        self._resolve_templates()
        self._resolve_links()
        self._validate()

        if skip_imports:
            return

        for index_config in self.indexes.values():
            if index_config.name in self._imports_resolved:
                continue

            _logger.info('Loading callbacks and typeclasses of index `%s`', index_config.name)

            if isinstance(index_config, IndexTemplateConfig):
                raise ConfigInitializationException

            elif isinstance(index_config, OperationIndexConfig):
                self._import_operation_index_types(index_config)
                self._import_index_callbacks(index_config)

            elif isinstance(index_config, BigMapIndexConfig):
                self._import_big_map_index_types(index_config)
                self._import_index_callbacks(index_config)

            else:
                raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

            self._imports_resolved.add(index_config.name)

    def _validate(self) -> None:
        # NOTE: Hasura
        if isinstance(self.database, SqliteDatabaseConfig) and self.hasura:
            raise ConfigurationError('SQLite database engine is not supported by Hasura')

        # NOTE: Reserved hooks
        for name, hook_config in self.hooks.items():
            if name != hook_config.callback:
                raise ConfigurationError(f'`{name}` hook name must be equal to `callback` value.')
            if name in default_hooks:
                raise ConfigurationError(f'`{name}` hook name is reserved. See docs to learn more about built-in hooks.')

        # NOTE: Duplicate contracts
        contracts = [cast(ResolvedIndexConfigT, i).contracts for i in self.indexes.values() if cast(ResolvedIndexConfigT, i).contracts]
        plain_contracts = reduce(operator.add, contracts) if contracts else []  # type: ignore
        # NOTE: After pre_initialize
        duplicate_contracts = [cast(ContractConfig, item).name for item, count in Counter(plain_contracts).items() if count > 1]
        if duplicate_contracts:
            _logger.warning(
                "The following contracts are used in more than one index: %s. Make sure you know what you're doing.",
                ' '.join(duplicate_contracts),
            )

        # NOTE: Callback uniqueness
        # TODO: Refactor, cover all cases
        for callback, pattern_items in self._callback_patterns.items():
            if len(pattern_items) in (0, 1):
                return

            def get_pattern_type(pattern_items: Sequence[HandlerPatternConfigT]) -> str:
                module_names = []
                for pattern_config in pattern_items:
                    if isinstance(pattern_config, OperationHandlerTransactionPatternConfig) and pattern_config.entrypoint:
                        module_names.append(pattern_config.destination_contract_config.module_name)
                    elif isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
                        module_names.append(pattern_config.module_name)
                    # TODO: Check BigMapHandlerPatternConfig
                return '::'.join(module_names)

            pattern_types = list(map(get_pattern_type, pattern_items))
            if any(map(lambda x: x != pattern_types[0], pattern_types)):
                _logger.warning(
                    'Callback `%s` used multiple times with different signatures. Make sure you have specified contract typenames',
                    callback,
                )

    def _resolve_template(self, template_config: IndexTemplateConfig) -> None:
        _logger.info('Resolving index config `%s` from template `%s`', template_config.name, template_config.template)

        template = self.get_template(template_config.template)
        raw_template = json.dumps(template, default=pydantic_encoder)
        for key, value in template_config.values.items():
            value_regex = r'<[ ]*' + key + r'[ ]*>'
            raw_template = re.sub(value_regex, value, raw_template)

        with suppress(AttributeError):
            missing_value = re.search(r'<*>', raw_template).search(0)  # type: ignore
            raise ConfigurationError(f'`{template_config.name}` index config is missing required template value `{missing_value}`')

        json_template = json.loads(raw_template)
        new_index_config = template.__class__(**json_template)
        new_index_config.template_values = template_config.values
        new_index_config.parent = template
        new_index_config.name = template_config.name
        self.indexes[template_config.name] = new_index_config

    def _resolve_templates(self) -> None:
        for index_config in self.indexes.values():
            if isinstance(index_config, IndexTemplateConfig):
                self._resolve_template(index_config)

    def _resolve_links(self) -> None:
        for name, index_config in self.indexes.items():
            if name in self._links_resolved:
                continue
            self._resolve_index_links(index_config)
            self._links_resolved.add(index_config.name)

        for job_config in self.jobs.values():
            if isinstance(job_config.hook, str):
                job_config.hook = self.hooks[job_config.hook]

    def _resolve_index_links(self, index_config: IndexConfigT) -> None:
        """Resolve contract and datasource configs by aliases"""

        if isinstance(index_config, OperationIndexConfig):
            if isinstance(index_config.datasource, str):
                index_config.datasource = self.get_tzkt_datasource(index_config.datasource)

            if index_config.contracts is not None:
                for i, contract in enumerate(index_config.contracts):
                    if isinstance(contract, str):
                        index_config.contracts[i] = self.get_contract(contract)

            for handler_config in index_config.handlers:
                handler_config.parent = index_config
                self._callback_patterns[handler_config.callback].append(handler_config.pattern)
                for pattern_config in handler_config.pattern:
                    transaction_id = 0
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
            if isinstance(index_config.datasource, str):
                index_config.datasource = self.get_tzkt_datasource(index_config.datasource)

            for handler in index_config.handlers:
                handler.parent = index_config
                # TODO: Verify callback uniqueness
                # self._callback_patterns[handler.callback].append(handler.pattern)
                if isinstance(handler.contract, str):
                    handler.contract = self.get_contract(handler.contract)

        else:
            raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

    def _set_names(self) -> None:
        # TODO: Forbid reusing names?
        named_config_sections = cast(
            Tuple[Dict[str, NameMixin], ...],
            (
                self.contracts,
                self.datasources,
                self.hooks,
                self.jobs,
                self.templates,
                self.indexes,
            ),
        )

        for named_configs in named_config_sections:
            for name, config in named_configs.items():
                config.name = name

    def _import_operation_index_types(self, index_config: OperationIndexConfig) -> None:
        for handler_config in index_config.handlers:
            for pattern_config in handler_config.pattern:
                if isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
                    if pattern_config.entrypoint:
                        module_name = pattern_config.destination_contract_config.module_name
                        pattern_config.initialize_parameter_cls(self.package, module_name, pattern_config.entrypoint)
                        pattern_config.initialize_storage_cls(self.package, module_name)
                elif isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
                    module_name = pattern_config.module_name
                    pattern_config.initialize_storage_cls(self.package, module_name)
                else:
                    raise NotImplementedError

    def _import_index_callbacks(self, index_config: ResolvedIndexConfigT) -> None:
        for handler_config in index_config.handlers:
            handler_config.initialize_callback_fn(self.package)

    def _import_big_map_index_types(self, index_config: BigMapIndexConfig) -> None:
        for big_map_handler_config in index_config.handlers:
            big_map_handler_config.initialize_big_map_type(self.package)


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
