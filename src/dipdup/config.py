import hashlib
import importlib
import json
import logging.config
import os
import re
from abc import ABC
from abc import abstractmethod
from collections import Counter
from collections import defaultdict
from contextlib import suppress
from copy import copy
from dataclasses import field
from functools import cached_property
from io import StringIO
from os import environ as env
from os.path import dirname
from pydoc import locate
from typing import Any
from typing import Callable
from typing import Dict
from typing import Generic
from typing import Iterator
from typing import List
from typing import Optional
from typing import Sequence
from typing import Set
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union
from typing import cast
from urllib.parse import urlparse

from pydantic import validator
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder
from ruamel.yaml import YAML
from typing_extensions import Literal

from dipdup.datasources.metadata.enums import MetadataNetwork
from dipdup.datasources.subscription import BigMapSubscription
from dipdup.datasources.subscription import OriginationSubscription
from dipdup.datasources.subscription import Subscription
from dipdup.datasources.subscription import TransactionSubscription
from dipdup.enums import OperationType
from dipdup.enums import ReindexingAction
from dipdup.enums import ReindexingReasonC
from dipdup.enums import SkipHistory
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import ConfigurationError
from dipdup.utils import exclude_none
from dipdup.utils import import_from
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal

ENV_VARIABLE_REGEX = r'\${([\w]*):-(.*)}'  # ${VARIABLE:-default}
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_SLEEP = 1
DEFAULT_METADATA_URL = 'https://metadata.dipdup.net'
DEFAULT_IPFS_URL = 'https://ipfs.io/ipfs'
DEFAULT_POSTGRES_SCHEMA = 'public'
DEFAULT_POSTGRES_USER = DEFAULT_POSTGRES_DATABASE = 'postgres'
DEFAULT_POSTGRES_PORT = 5432
DEFAULT_SQLITE_PATH = ':memory'

_logger = logging.getLogger('dipdup.config')


@dataclass
class SqliteDatabaseConfig:
    """
    SQLite connection config

    :param kind: always 'sqlite'
    :param path: Path to .sqlite3 file, leave default for in-memory database
    """

    kind: Literal['sqlite']
    path: str = DEFAULT_SQLITE_PATH

    @cached_property
    def connection_string(self) -> str:
        return f'{self.kind}://{self.path}'


@dataclass
class PostgresDatabaseConfig:
    """Postgres database connection config

    :param kind: always 'postgres'
    :param host: Host
    :param port: Port
    :param user: User
    :param password: Password
    :param database: Database name
    :param schema_name: Schema name
    :param immune_tables: List of tables to preserve during reindexing
    :param connection_timeout: Connection timeout
    """

    kind: Literal['postgres']
    host: str
    user: str = DEFAULT_POSTGRES_USER
    database: str = DEFAULT_POSTGRES_DATABASE
    port: int = DEFAULT_POSTGRES_PORT
    schema_name: str = DEFAULT_POSTGRES_SCHEMA
    password: str = ''
    immune_tables: Tuple[str, ...] = field(default_factory=tuple)
    connection_timeout: int = 60

    @cached_property
    def connection_string(self) -> str:
        # NOTE: `maxsize=1` is important! Concurrency will be broken otherwise.
        # NOTE: https://github.com/tortoise/tortoise-orm/issues/792
        connection_string = f'{self.kind}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?maxsize=1'
        if self.schema_name != DEFAULT_POSTGRES_SCHEMA:
            connection_string += f'&schema={self.schema_name}'
        return connection_string

    @validator('immune_tables')
    def valid_immune_tables(cls, v):
        for table in v:
            if table.startswith('dipdup'):
                raise ConfigurationError('Tables with `dipdup` prefix can\'t be immune')
        return v


@dataclass
class HTTPConfig:
    """Advanced configuration of HTTP client

    :param cache: Whether to cache responses
    :param retry_count: Number of retries before giving up
    :param retry_sleep: Sleep time between retries
    :param retry_multiplier: Multiplier for sleep time between retries
    :param ratelimit_rate: Number of requests per `ratelimit_period`
    :param ratelimit_period: Time period for rate limiting
    :param connection_limit: Number of simultaneous connections
    :param connection_timeout: Connection timeout
    :param batch_size: Number of items fetched in a single request
    """

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

    @cached_property
    def name(self) -> str:
        if self._name is None:
            raise ConfigInitializationException
        return self._name


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

    @cached_property
    def module_name(self) -> str:
        return self.typename or self.name

    @validator('address', allow_reuse=True)
    def valid_address(cls, v):
        # NOTE: Environment substitution disabled
        if '$' in v:
            return v

        # NOTE: Wallet addresses are allowed for debugging purposes (source field). Do we need a separate section?
        if not (v.startswith('KT') or v.startswith('tz')) or len(v) != 36:
            raise ConfigurationError(f'`{v}` is not a valid contract address')
        return v


# NOTE: Don't forget `http` and `__hash__` in all datasource configs
@dataclass
class TzktDatasourceConfig(NameMixin):
    """TzKT datasource config

    :param kind: always 'tzkt'
    :param url: Base API URL, e.g. https://api.tzkt.io/
    :param http: HTTP client configuration
    """

    kind: Literal['tzkt']
    url: str
    http: Optional[HTTPConfig] = None

    def __hash__(self):
        return hash(self.kind + self.url)

    def __post_init_post_parse__(self) -> None:
        super().__post_init_post_parse__()
        if self.http and self.http.batch_size and self.http.batch_size > 10000:
            raise ConfigurationError('`batch_size` must be less than 10000')
        parsed_url = urlparse(self.url)
        # NOTE: Environment substitution disabled
        if '$' in self.url:
            return
        if not (parsed_url.scheme and parsed_url.netloc):
            raise ConfigurationError(f'`{self.url}` is not a valid datasource URL')


@dataclass
class CoinbaseDatasourceConfig(NameMixin):
    """Coinbase datasource config

    :param kind: always 'coinbase'
    :param api_key: API key
    :param secret_key: API secret key
    :param passphrase: API passphrase
    :param http: HTTP client configuration
    """

    kind: Literal['coinbase']
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    passphrase: Optional[str] = None
    http: Optional[HTTPConfig] = None

    def __hash__(self):
        return hash(self.kind)


@dataclass
class MetadataDatasourceConfig(NameMixin):
    kind: Literal['metadata']
    network: MetadataNetwork
    url: str = DEFAULT_METADATA_URL
    http: Optional[HTTPConfig] = None

    def __hash__(self):
        return hash(self.kind + self.url + self.network.value)


@dataclass
class IpfsDatasourceConfig(NameMixin):
    kind: Literal['ipfs']
    url: str = DEFAULT_IPFS_URL
    http: Optional[HTTPConfig] = None

    def __hash__(self):
        return hash(self.kind + self.url)


@dataclass
class HttpDatasourceConfig(NameMixin):
    kind: Literal['http']
    url: str
    http: Optional[HTTPConfig] = None

    def __hash__(self):
        return hash(self.kind + self.url)


DatasourceConfigT = Union[
    TzktDatasourceConfig,
    CoinbaseDatasourceConfig,
    MetadataDatasourceConfig,
    IpfsDatasourceConfig,
    HttpDatasourceConfig,
]


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
    def format_untyped_operation_import(cls) -> Tuple[str, str]:
        return 'dipdup.models', 'OperationData'

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
    def format_untyped_operation_argument(cls, transaction_id: int, optional: bool) -> Tuple[str, str]:
        if optional:
            return f'transaction_{transaction_id}', 'Optional[OperationData] = None'
        return f'transaction_{transaction_id}', 'OperationData'


@dataclass
class StorageTypeMixin:
    """`storage_type_cls` field"""

    def __post_init_post_parse__(self):
        self._storage_type_cls = None

    @cached_property
    def storage_type_cls(self) -> Type:
        if self._storage_type_cls is None:
            raise ConfigInitializationException
        return self._storage_type_cls

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

    @cached_property
    def parent(self) -> Optional[T]:
        return self._parent


@dataclass
class ParameterTypeMixin:
    """`parameter_type_cls` field"""

    def __post_init_post_parse__(self):
        self._parameter_type_cls = None

    @cached_property
    def parameter_type_cls(self) -> Type:
        if self._parameter_type_cls is None:
            raise ConfigInitializationException
        return self._parameter_type_cls

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

    @cached_property
    def transaction_id(self) -> int:
        if self._transaction_id is None:
            raise ConfigInitializationException
        return self._transaction_id


@dataclass
class OperationHandlerTransactionPatternConfig(PatternConfig, StorageTypeMixin, ParameterTypeMixin, TransactionIdMixin):
    """Operation handler pattern config

    :param type: always 'transaction'
    :param source: Source contract alias to filter operations with
    :param destination: Destination contract alias to filter operations with
    :param entrypoint: Contract entrypoint to filter operations with
    :param optional: Whether can operation be missing in operation group
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
        if self.entrypoint:
            module_name = self.destination_contract_config.module_name
            yield 'dipdup.models', 'Transaction'
            yield self.format_parameter_import(package, module_name, self.entrypoint)
            yield self.format_storage_import(package, module_name)
        else:
            yield self.format_untyped_operation_import()

    def iter_arguments(self) -> Iterator[Tuple[str, str]]:
        if self.entrypoint:
            module_name = self.destination_contract_config.module_name
            yield self.format_operation_argument(module_name, self.entrypoint, self.optional)
        else:
            yield self.format_untyped_operation_argument(self.transaction_id, self.optional)

    @cached_property
    def source_contract_config(self) -> ContractConfig:
        if not isinstance(self.source, ContractConfig):
            raise ConfigInitializationException
        return self.source

    @cached_property
    def destination_contract_config(self) -> ContractConfig:
        if not isinstance(self.destination, ContractConfig):
            raise ConfigInitializationException
        return self.destination


@dataclass
class OperationHandlerOriginationPatternConfig(PatternConfig, StorageTypeMixin):
    """Origination handler pattern config

    :param source: Source contract alias to filter operations with
    :param similar_to: Alias of contract having the same code/signature (depending on `strict` field)
    """

    type: Literal['origination'] = 'origination'
    source: Optional[Union[str, ContractConfig]] = None
    similar_to: Optional[Union[str, ContractConfig]] = None
    originated_contract: Optional[Union[str, ContractConfig]] = None
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

    @cached_property
    def module_name(self) -> str:
        return self.contract_config.module_name

    @cached_property
    def contract_config(self) -> ContractConfig:
        if self.originated_contract:
            return self.originated_contract_config
        if self.similar_to:
            return self.similar_to_contract_config
        if self.source:
            return self.source_contract_config
        raise RuntimeError

    @cached_property
    def source_contract_config(self) -> ContractConfig:
        if not isinstance(self.source, ContractConfig):
            raise ConfigInitializationException
        return self.source

    @cached_property
    def similar_to_contract_config(self) -> ContractConfig:
        if not isinstance(self.similar_to, ContractConfig):
            raise ConfigInitializationException
        return self.similar_to

    @cached_property
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
        if self.callback and self.callback != pascal_to_snake(self.callback, strip_dots=False):
            raise ConfigurationError('`callback` field must be a valid Python module name')

    @cached_property
    def kind(self) -> str:
        return self._kind  # type: ignore

    @cached_property
    def callback_fn(self) -> Callable:
        if self._callback_fn is None:
            raise ConfigInitializationException
        return self._callback_fn

    def initialize_callback_fn(self, package: str):
        if self._callback_fn:
            return
        _logger.debug('Registering %s callback `%s`', self.kind, self.callback)
        module_name = f'{package}.{self.kind}s.{self.callback}'
        fn_name = self.callback.rsplit('.', 1)[-1]
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

    pattern: Tuple[OperationHandlerPatternConfigT, ...]

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

    @cached_property
    def template_values(self) -> Dict[str, str]:
        return self._template_values


@dataclass
class SubscriptionsMixin:
    def __post_init_post_parse__(self) -> None:
        self.subscriptions: Set[Subscription] = set()


@dataclass
class IndexTemplateConfig(NameMixin):
    kind = 'template'
    template: str
    values: Dict[str, str]
    first_level: int = 0
    last_level: int = 0


@dataclass
class IndexConfig(TemplateValuesMixin, NameMixin, SubscriptionsMixin, ParentMixin['ResolvedIndexConfigT']):
    datasource: Union[str, TzktDatasourceConfig]

    def __post_init_post_parse__(self) -> None:
        TemplateValuesMixin.__post_init_post_parse__(self)
        NameMixin.__post_init_post_parse__(self)
        SubscriptionsMixin.__post_init_post_parse__(self)
        ParentMixin.__post_init_post_parse__(self)

    @cached_property
    def datasource_config(self) -> TzktDatasourceConfig:
        if not isinstance(self.datasource, TzktDatasourceConfig):
            raise ConfigInitializationException
        return self.datasource

    def hash(self) -> str:
        """Calculate hash to ensure config not changed since last run."""
        config_json = json.dumps(self, default=pydantic_encoder)

        # FIXME: How to convert pydantic dataclass into dict without json.dumps? asdict is not recursive.
        config_dict = json.loads(config_json)

        # NOTE: We need to preserve datasource URL but remove it's HTTP tunables to avoid false-positives.
        config_dict['datasource'].pop('http', None)
        # NOTE: Same for BigMapIndex tunables
        config_dict.pop('skip_history', None)

        config_json = json.dumps(config_dict)
        return hashlib.sha256(config_json.encode()).hexdigest()


@dataclass
class OperationIndexConfig(IndexConfig):
    """Operation index config

    :param datasource: Alias of index datasource in `datasources` section
    :param contracts: Aliases of contracts being indexed in `contracts` section
    :param first_level: First block to process (one time sync)
    :param last_level: Last block to process (one time sync)
    :param handlers: List of indexer handlers
    """

    kind: Literal["operation"]
    handlers: Tuple[OperationHandlerConfig, ...]
    types: Tuple[OperationType, ...] = (OperationType.transaction,)
    contracts: List[Union[str, ContractConfig]] = field(default_factory=list)

    first_level: int = 0
    last_level: int = 0

    @cached_property
    def entrypoint_filter(self) -> Set[Optional[str]]:
        entrypoints = set()
        for handler_config in self.handlers:
            for pattern_config in handler_config.pattern:
                if isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
                    entrypoints.add(pattern_config.entrypoint)
        return set(entrypoints)

    @cached_property
    def address_filter(self) -> Set[str]:
        addresses = set()
        for handler_config in self.handlers:
            for pattern_config in handler_config.pattern:
                if isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
                    if isinstance(pattern_config.source, ContractConfig):
                        addresses.add(pattern_config.source.address)
                    elif isinstance(pattern_config.source, str):
                        raise ConfigInitializationException

                    if isinstance(pattern_config.destination, ContractConfig):
                        addresses.add(pattern_config.destination.address)
                    elif isinstance(pattern_config.destination, str):
                        raise ConfigInitializationException

        return addresses


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
        key_cls = f'{snake_to_pascal(path)}Key'
        key_module = f'{pascal_to_snake(path)}_key'
        return f'{package}.types.{module_name}.big_map.{key_module}', key_cls

    @classmethod
    def format_value_import(cls, package: str, module_name: str, path: str) -> Tuple[str, str]:
        value_cls = f'{snake_to_pascal(path)}Value'
        value_module = f'{pascal_to_snake(path)}_value'
        return f'{package}.types.{module_name}.big_map.{value_module}', value_cls

    @classmethod
    def format_big_map_diff_argument(cls, path: str) -> Tuple[str, str]:
        key_cls = f'{snake_to_pascal(path)}Key'
        value_cls = f'{snake_to_pascal(path)}Value'
        return pascal_to_snake(path), f'BigMapDiff[{key_cls}, {value_cls}]'

    def iter_imports(self, package: str) -> Iterator[Tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models', 'BigMapDiff'
        yield package, 'models as models'

        yield self.format_key_import(package, self.contract_config.module_name, self.path)
        yield self.format_value_import(package, self.contract_config.module_name, self.path)

    def iter_arguments(self) -> Iterator[Tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield self.format_big_map_diff_argument(self.path)

    @cached_property
    def contract_config(self) -> ContractConfig:
        if not isinstance(self.contract, ContractConfig):
            raise ConfigInitializationException
        return self.contract

    @cached_property
    def key_type_cls(self) -> Type:
        if self._key_type_cls is None:
            raise ConfigInitializationException
        return self._key_type_cls

    @cached_property
    def value_type_cls(self) -> Type:
        if self._value_type_cls is None:
            raise ConfigInitializationException
        return self._value_type_cls

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
    handlers: Tuple[BigMapHandlerConfig, ...]

    skip_history: SkipHistory = SkipHistory.never

    first_level: int = 0
    last_level: int = 0

    @cached_property
    def contracts(self) -> Set[ContractConfig]:
        return {handler_config.contract_config for handler_config in self.handlers}


@dataclass
class HeadHandlerConfig(HandlerConfig, kind='handler'):
    def iter_imports(self, package: str) -> Iterator[Tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models', 'HeadBlockData'
        yield package, 'models as models'

    def iter_arguments(self) -> Iterator[Tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield 'head', 'HeadBlockData'


@dataclass
class HeadIndexConfig(IndexConfig):
    kind: Literal['head']
    datasource: Union[str, TzktDatasourceConfig]
    handlers: Tuple[HeadHandlerConfig, ...]


IndexConfigT = Union[OperationIndexConfig, BigMapIndexConfig, HeadIndexConfig, IndexTemplateConfig]
ResolvedIndexConfigT = Union[OperationIndexConfig, BigMapIndexConfig, HeadIndexConfig]
ContractIndexConfigT = Union[OperationIndexConfig, BigMapIndexConfig]
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

    @cached_property
    def headers(self) -> Dict[str, str]:
        if self.admin_secret:
            return {'X-Hasura-Admin-Secret': self.admin_secret}
        return {}


@dataclass
class JobConfig(NameMixin):
    hook: Union[str, 'HookConfig']
    crontab: Optional[str] = None
    interval: Optional[int] = None
    daemon: bool = False
    args: Dict[str, Any] = field(default_factory=dict)

    def __post_init_post_parse__(self):
        if self.crontab and self.interval:
            raise ConfigurationError('Only one of `crontab` and `interval` can be specified')
        elif not (self.crontab or self.interval or self.daemon):
            raise ConfigurationError('One of `crontab`, `interval` or `daemon` must be specified')

        NameMixin.__post_init_post_parse__(self)

    @cached_property
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
class PrometheusConfig:
    host: str
    port: int = 8000
    update_interval: float = 1.0


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


default_hooks = {
    # NOTE: After schema initialization. Default: nothing.
    'on_restart': HookConfig(
        callback='on_restart',
    ),
    # NOTE: On reorg message. Default: reindex.
    'on_rollback': HookConfig(
        callback='on_rollback',
        args={
            'datasource': 'dipdup.datasources.datasource.Datasource',
            'from_level': 'int',
            'to_level': 'int',
        },
    ),
    # NOTE: After restart (important!) after ctx.reindex call. Default: nothing.
    'on_reindex': HookConfig(
        callback='on_reindex',
    ),
    # NOTE: All indexes are in REALTIME state. Default: nothing.
    'on_synchronized': HookConfig(
        callback='on_synchronized',
    ),
}


@dataclass
class AdvancedConfig:
    reindex: Dict[ReindexingReasonC, ReindexingAction] = field(default_factory=dict)
    scheduler: Optional[Dict[str, Any]] = None
    # TODO: Drop in major version
    oneshot: bool = False
    postpone_jobs: bool = False
    early_realtime: bool = False
    merge_subscriptions: bool = False
    metadata_interface: bool = False


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
    :param advanced: Advanced config
    """

    spec_version: str
    package: str
    datasources: Dict[str, DatasourceConfigT]
    database: Union[SqliteDatabaseConfig, PostgresDatabaseConfig] = SqliteDatabaseConfig(kind='sqlite')
    contracts: Dict[str, ContractConfig] = field(default_factory=dict)
    indexes: Dict[str, IndexConfigT] = field(default_factory=dict)
    templates: Dict[str, ResolvedIndexConfigT] = field(default_factory=dict)
    jobs: Dict[str, JobConfig] = field(default_factory=dict)
    hooks: Dict[str, HookConfig] = field(default_factory=dict)
    hasura: Optional[HasuraConfig] = None
    sentry: Optional[SentryConfig] = None
    prometheus: Optional[PrometheusConfig] = None
    advanced: AdvancedConfig = AdvancedConfig()

    def __post_init_post_parse__(self):
        self.paths: List[str] = []
        self.environment: Dict[str, str] = {}
        self._callback_patterns: Dict[str, List[Sequence[HandlerPatternConfigT]]] = defaultdict(list)
        self._default_hooks: bool = False
        self._links_resolved: Set[str] = set()
        self._imports_resolved: Set[str] = set()
        self._package_path: Optional[str] = None

    @cached_property
    def schema_name(self) -> str:
        if isinstance(self.database, PostgresDatabaseConfig):
            return self.database.schema_name
        # NOTE: Not exactly correct; historical reason
        return DEFAULT_POSTGRES_SCHEMA

    @cached_property
    def package_path(self) -> str:
        if not self._package_path:
            package = importlib.import_module(self.package)
            self._package_path = dirname(package.__file__)

        return self._package_path

    @property
    def oneshot(self) -> bool:
        syncable_indexes = tuple(c for c in self.indexes.values() if not isinstance(c, HeadIndexConfig))
        oneshot_indexes = tuple(c for c in syncable_indexes if c.last_level)
        if not oneshot_indexes:
            return False
        elif len(oneshot_indexes) == len(syncable_indexes):
            return True
        else:
            raise ConfigurationError('Either all or none of indexes can have `last_level` field set')

    @classmethod
    def load(
        cls,
        paths: List[str],
        environment: bool = True,
    ) -> 'DipDupConfig':
        yaml = YAML(typ='base')
        current_workdir = os.path.join(os.getcwd())

        json_config: Dict[str, Any] = {}
        config_environment: Dict[str, str] = {}
        for path in paths:
            path = os.path.join(current_workdir, path)

            _logger.debug('Loading config from %s', path)
            try:
                with open(path) as file:
                    raw_config = file.read()
            except OSError as e:
                raise ConfigurationError(str(e))

            if environment:
                _logger.debug('Substituting environment variables')
                for match in re.finditer(ENV_VARIABLE_REGEX, raw_config):
                    variable, default_value = match.group(1), match.group(2)
                    config_environment[variable] = default_value
                    value = env.get(variable)
                    if not default_value and not value:
                        raise ConfigurationError(f'Environment variable `{variable}` is not set')
                    placeholder = '${' + variable + ':-' + default_value + '}'
                    raw_config = raw_config.replace(placeholder, value or default_value)

            json_config.update(yaml.load(raw_config))

        try:
            config = cls(**json_config)
            config.environment = config_environment
            config.paths = paths
        except Exception as e:
            raise ConfigurationError(str(e)) from e
        return config

    def dump(self) -> str:
        yaml = YAML(typ='unsafe', pure=True)
        yaml.default_flow_style = False
        yaml.indent = 2

        config_json = json.dumps(self, default=pydantic_encoder)
        config_yaml = exclude_none(yaml.load(config_json))
        buffer = StringIO()
        yaml.dump(config_yaml, buffer)
        return buffer.getvalue()

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

    def get_index(self, name: str) -> IndexConfigT:
        try:
            return self.indexes[name]
        except KeyError as e:
            raise ConfigurationError(f'Index `{name}` not found in `indexes` config section') from e

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

            _logger.debug('Loading callbacks and typeclasses of index `%s`', index_config.name)

            if isinstance(index_config, IndexTemplateConfig):
                raise ConfigInitializationException

            elif isinstance(index_config, OperationIndexConfig):
                self._import_operation_index_types(index_config)
                self._import_index_callbacks(index_config)

            elif isinstance(index_config, BigMapIndexConfig):
                self._import_big_map_index_types(index_config)
                self._import_index_callbacks(index_config)

            elif isinstance(index_config, HeadIndexConfig):
                self._import_index_callbacks(index_config)

            else:
                raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

            self._imports_resolved.add(index_config.name)

    def _validate(self) -> None:
        # NOTE: Hasura and metadata interface
        if self.hasura:
            if isinstance(self.database, SqliteDatabaseConfig):
                raise ConfigurationError('SQLite database engine is not supported by Hasura')
            if self.advanced.metadata_interface and self.hasura.camel_case:
                raise ConfigurationError('`metadata_interface` flag is incompatible with `camel_case` one')
        else:
            if self.advanced.metadata_interface:
                raise ConfigurationError('`metadata_interface` flag requires `hasura` section to be present')

        # NOTE: Reserved hooks
        for name, hook_config in self.hooks.items():
            if name != hook_config.callback:
                raise ConfigurationError(f'`{name}` hook name must be equal to `callback` value.')
            if name in default_hooks:
                raise ConfigurationError(f'`{name}` hook name is reserved. See docs to learn more about built-in hooks.')

    def _resolve_template(self, template_config: IndexTemplateConfig) -> None:
        _logger.debug('Resolving index config `%s` from template `%s`', template_config.name, template_config.template)

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
        if not isinstance(new_index_config, HeadIndexConfig):
            new_index_config.first_level |= template_config.first_level
            new_index_config.last_level |= template_config.last_level
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
            # TODO: Not exactly link resolving, move somewhere else
            self._resolve_index_subscriptions(index_config)
            self._links_resolved.add(index_config.name)

        for job_config in self.jobs.values():
            if isinstance(job_config.hook, str):
                hook_config = self.get_hook(job_config.hook)
                if job_config.daemon and hook_config.atomic:
                    raise ConfigurationError('`HookConfig.atomic` and `JobConifg.daemon` flags are mutually exclusive')
                job_config.hook = hook_config

    def _resolve_index_subscriptions(self, index_config: IndexConfigT) -> None:
        if isinstance(index_config, IndexTemplateConfig):
            return
        if index_config.subscriptions:
            return

        if isinstance(index_config, OperationIndexConfig):
            if self.advanced.merge_subscriptions:
                index_config.subscriptions.add(TransactionSubscription())
            else:
                for contract_config in index_config.contracts:
                    if not isinstance(contract_config, ContractConfig):
                        raise ConfigInitializationException
                    index_config.subscriptions.add(TransactionSubscription(address=contract_config.address))

            for handler_config in index_config.handlers:
                for pattern_config in handler_config.pattern:
                    if isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
                        index_config.subscriptions.add(OriginationSubscription())
                        break

        elif isinstance(index_config, BigMapIndexConfig):
            if self.advanced.merge_subscriptions:
                index_config.subscriptions.add(BigMapSubscription())
            else:
                for big_map_handler_config in index_config.handlers:
                    address, path = big_map_handler_config.contract_config.address, big_map_handler_config.path
                    index_config.subscriptions.add(BigMapSubscription(address=address, path=path))

        # NOTE: HeadSubscription is always enabled
        elif isinstance(index_config, HeadIndexConfig):
            pass

        else:
            raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

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
                for idx, pattern_config in enumerate(handler_config.pattern):
                    # NOTE: Untyped operations are named as `transaction_N` based on their index
                    if isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
                        if isinstance(pattern_config.destination, str):
                            pattern_config.destination = self.get_contract(pattern_config.destination)
                        if isinstance(pattern_config.source, str):
                            pattern_config.source = self.get_contract(pattern_config.source)
                        if not pattern_config.entrypoint:
                            pattern_config.transaction_id = idx

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

        elif isinstance(index_config, HeadIndexConfig):
            if isinstance(index_config.datasource, str):
                index_config.datasource = self.get_tzkt_datasource(index_config.datasource)

            for head_handler_config in index_config.handlers:
                head_handler_config.parent = index_config

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
        path: str,
    ) -> 'LoggingConfig':

        current_workdir = os.path.join(os.getcwd())
        path = os.path.join(current_workdir, path)

        with open(path) as file:
            return cls(config=YAML().load(file.read()))

    def apply(self):
        logging.config.dictConfig(self.config)
