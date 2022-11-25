"""Config files parsing and processing

As you can see from the amount of code below, lots of things are going on here:

* YAML (de)serialization
* Templating indexes and env variables (`<...>` and `${...}` syntax)
* Config initialization and validation
* Methods to generate paths for codegen
* And even importing contract types on demand

Dataclasses are used in this module instead of BaseModel for historical reasons (can't remember why;
something about ruamel.yaml compatibility), thus "...Mixin" classes to workaround the lack of proper
inheritance.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import logging.config
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
from pathlib import Path
from pydoc import locate
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Generic
from typing import Iterator
from typing import Sequence
from typing import TypeVar
from typing import cast
from urllib.parse import quote_plus
from urllib.parse import urlparse

from pydantic import Field
from pydantic import validator
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder
from ruamel.yaml import YAML
from typing_extensions import Literal

from dipdup import baking_bad
from dipdup.datasources.metadata.enums import MetadataNetwork
from dipdup.datasources.subscription import Subscription
from dipdup.datasources.tzkt.models import BigMapSubscription
from dipdup.datasources.tzkt.models import EventSubscription
from dipdup.datasources.tzkt.models import HeadSubscription
from dipdup.datasources.tzkt.models import OriginationSubscription
from dipdup.datasources.tzkt.models import TokenTransferSubscription
from dipdup.datasources.tzkt.models import TransactionSubscription
from dipdup.enums import LoggingValues
from dipdup.enums import OperationType
from dipdup.enums import ReindexingAction
from dipdup.enums import ReindexingReason
from dipdup.enums import SkipHistory
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import IndexAlreadyExistsError
from dipdup.utils import exclude_none
from dipdup.utils import import_from
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal
from dipdup.utils.sys import is_in_tests

# NOTE: ${VARIABLE:-default} | ${VARIABLE}
ENV_VARIABLE_REGEX = r'\$\{(?P<var_name>[\w]+)(?:\:\-(?P<default_value>.*?))?\}'
DEFAULT_METADATA_URL = baking_bad.METADATA_API_URL
DEFAULT_IPFS_URL = 'https://ipfs.io/ipfs'
DEFAULT_TZKT_URL = next(iter(baking_bad.TZKT_API_URLS.keys()))
DEFAULT_POSTGRES_SCHEMA = 'public'
DEFAULT_POSTGRES_DATABASE = 'postgres'
DEFAULT_POSTGRES_USER = 'postgres'
DEFAULT_POSTGRES_PORT = 5432
DEFAULT_SQLITE_PATH = ':memory:'

ADDRESS_PREFIXES = (
    'KT1',
    # NOTE: Wallet addresses are allowed during config validation for debugging purposes.
    # NOTE: It's a undocumented hack to filter by `source` field. Wallet indexing is not supported.
    # NOTE: See https://github.com/dipdup-io/dipdup/issues/291
    'tz1',
    'tz2',
    'tz3',
)

_logger = logging.getLogger('dipdup.config')


@dataclass
class SqliteDatabaseConfig:
    """
    SQLite connection config

    :param kind: always 'sqlite'
    :param path: Path to .sqlite3 file, leave default for in-memory database (`:memory:`)
    """

    kind: Literal['sqlite']
    path: str = DEFAULT_SQLITE_PATH

    @property
    def schema_name(self) -> str:
        return 'public'

    @property
    def connection_string(self) -> str:
        return f'{self.kind}://{self.path}'

    @property
    def immune_tables(self) -> set[str]:
        return set()

    @property
    def connection_timeout(self) -> int:
        # NOTE: Fail immediately
        return 1


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
    password: str = field(default='', repr=False)
    immune_tables: set[str] = field(default_factory=set)
    connection_timeout: int = 60

    @cached_property
    def connection_string(self) -> str:
        # NOTE: `maxsize=1` is important! Concurrency will be broken otherwise.
        # NOTE: https://github.com/tortoise/tortoise-orm/issues/792
        connection_string = (
            f'{self.kind}://{self.user}:{quote_plus(self.password)}@{self.host}:{self.port}/{self.database}?maxsize=1'
        )
        if self.schema_name != DEFAULT_POSTGRES_SCHEMA:
            connection_string += f'&schema={self.schema_name}'
        return connection_string

    @cached_property
    def hasura_connection_parameters(self) -> dict[str, Any]:
        return {
            'username': self.user,
            'password': self.password,
            'database': self.database,
            'host': self.host,
            'port': self.port,
        }

    @validator('immune_tables', allow_reuse=True)
    def _valid_immune_tables(cls, v: set[str]) -> set[str]:
        for table in v:
            if table.startswith('dipdup'):
                raise ConfigurationError("Tables with `dipdup` prefix can't be immune")
        return v


@dataclass
class HTTPConfig:
    """Advanced configuration of HTTP client

    :param retry_count: Number of retries after request failed before giving up
    :param retry_sleep: Sleep time between retries
    :param retry_multiplier: Multiplier for sleep time between retries
    :param ratelimit_rate: Number of requests per period ("drops" in leaky bucket)
    :param ratelimit_period: Time period for rate limiting in seconds
    :param connection_limit: Number of simultaneous connections
    :param connection_timeout: Connection timeout in seconds
    :param batch_size: Number of items fetched in a single paginated request (for some APIs)
    :param replay_path: Development-only option to replay HTTP requests from a file
    """

    retry_count: int | None = None         # default: inf
    retry_sleep: float | None = None       # default: 0
    retry_multiplier: float | None = None  # default: 0
    ratelimit_rate: int | None = None
    ratelimit_period: int | None = None
    connection_limit: int | None = None    # default: 100
    connection_timeout: int | None = None  # default: 60
    batch_size: int | None = None
    replay_path: str | None = None

    def merge(self, other: HTTPConfig | None) -> 'HTTPConfig':
        """Set missing values from other config"""
        config = copy(self)
        if other:
            for k, v in other.__dict__.items():
                if v is not None:
                    setattr(config, k, v)
        return config


@dataclass
class NameMixin:
    def __post_init_post_parse__(self) -> None:
        self._name: str | None = None

    @cached_property
    def name(self) -> str:
        if self._name is None:
            raise ConfigInitializationException(f'{self.__class__.__name__} name is not set')
        return self._name


@dataclass
class ContractConfig(NameMixin):
    """Contract config

    :param address: Contract address
    :param typename: User-defined alias for the contract script
    """

    address: str
    typename: str | None = None

    def __hash__(self) -> int:
        return hash(f'{self.address}{self.typename or ""}')

    @cached_property
    def module_name(self) -> str:
        return self.typename or self.name

    @validator('address', allow_reuse=True)
    def _valid_address(cls, v: str) -> str:
        # NOTE: Environment substitution was disabled during export, skip validation
        if '$' in v:
            return v

        if not v.startswith(ADDRESS_PREFIXES) or len(v) != 36:
            raise ConfigurationError(f'`{v}` is not a valid contract address')
        return v


class DatasourceConfig(ABC, NameMixin):
    kind: str
    http: HTTPConfig | None

    @abstractmethod
    def __hash__(self) -> int:
        ...


@dataclass
class TzktDatasourceConfig(DatasourceConfig):
    """TzKT datasource config

    :param kind: always 'tzkt'
    :param url: Base API URL, e.g. https://api.tzkt.io/
    :param http: HTTP client configuration
    :param buffer_size: Number of levels to keep in FIFO buffer before processing
    """

    kind: Literal['tzkt']
    url: str = DEFAULT_TZKT_URL
    http: HTTPConfig | None = None
    buffer_size: int = 0

    def __hash__(self) -> int:
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
class CoinbaseDatasourceConfig(DatasourceConfig):
    """Coinbase datasource config

    :param kind: always 'coinbase'
    :param api_key: API key
    :param secret_key: API secret key
    :param passphrase: API passphrase
    :param http: HTTP client configuration
    """

    kind: Literal['coinbase']
    api_key: str | None = None
    secret_key: str | None = None
    passphrase: str | None = None
    http: HTTPConfig | None = None

    def __hash__(self) -> int:
        return hash(self.kind)


@dataclass
class MetadataDatasourceConfig(NameMixin):
    """DipDup Metadata datasource config

    :param kind: always 'metadata'
    :param network: Network name, e.g. mainnet, ghostnet, etc.
    :param url: GraphQL API URL, e.g. https://metadata.dipdup.net
    :param http: HTTP client configuration
    """

    kind: Literal['metadata']
    network: MetadataNetwork
    url: str = DEFAULT_METADATA_URL
    http: HTTPConfig | None = None

    def __hash__(self) -> int:
        return hash(self.kind + self.url + self.network.value)


@dataclass
class IpfsDatasourceConfig(DatasourceConfig):
    """IPFS datasource config

    :param kind: always 'ipfs'
    :param url: IPFS node URL, e.g. https://ipfs.io/ipfs/
    :param http: HTTP client configuration
    """

    kind: Literal['ipfs']
    url: str = DEFAULT_IPFS_URL
    http: HTTPConfig | None = None

    def __hash__(self) -> int:
        return hash(self.kind + self.url)


@dataclass
class HttpDatasourceConfig(DatasourceConfig):
    """Generic HTTP datasource config

    kind: always 'http'
    url: URL to fetch data from
    http: HTTP client configuration
    """

    kind: Literal['http']
    url: str
    http: HTTPConfig | None = None

    def __hash__(self) -> int:
        return hash(self.kind + self.url)


# NOTE: We need unions for Pydantic deserialization
DatasourceConfigU = (
    TzktDatasourceConfig
    | CoinbaseDatasourceConfig
    | MetadataDatasourceConfig
    | IpfsDatasourceConfig
    | HttpDatasourceConfig
)


@dataclass
class CodegenMixin(ABC):
    """Base for pattern config classes containing methods required for codegen"""

    @abstractmethod
    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        ...

    @abstractmethod
    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        ...

    def format_imports(self, package: str) -> Iterator[str]:
        for package_name, cls in self.iter_imports(package):
            yield f'from {package_name} import {cls}'

    def format_arguments(self) -> Iterator[str]:
        arguments = list(self.iter_arguments())
        i, counter = 0, Counter(name for name, _ in arguments)

        for name, cls in arguments:
            if counter[name] > 1:
                yield f'{name}_{i}: {cls}'
                i += 1
            else:
                yield f'{name}: {cls}'

    def locate_arguments(self) -> dict[str, type | None]:
        """Try to resolve scope annotations for arguments"""
        kwargs: dict[str, type[Any] | None] = {}
        for name, cls in self.iter_arguments():
            cls = cls.split(' as ')[0]
            kwargs[name] = cast(type | None, locate(cls))
        return kwargs


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
        return 'dipdup.models', 'OperationData'

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
class StorageTypeMixin:
    """`storage_type_cls` field"""

    def __post_init_post_parse__(self) -> None:
        self._storage_type_cls: type[Any] | None = None

    @cached_property
    def storage_type_cls(self) -> type[Any]:
        if self._storage_type_cls is None:
            raise ConfigInitializationException
        return self._storage_type_cls

    def initialize_storage_cls(self, package: str, module_name: str) -> None:
        _logger.debug('Registering `%s` storage type', module_name)
        cls_name = snake_to_pascal(module_name) + 'Storage'
        module_name = f'{package}.types.{module_name}.storage'
        self.storage_type_cls = import_from(module_name, cls_name)


ParentT = TypeVar('ParentT')


@dataclass
class ParentMixin(Generic[ParentT]):
    """`parent` field for index and template configs"""

    def __post_init_post_parse__(self: ParentMixin[ParentT]) -> None:
        self._parent: ParentT | None = None

    @property
    def parent(self) -> ParentT | None:
        return self._parent

    @parent.setter
    def parent(self, value: ParentT) -> None:
        self._parent = value


@dataclass
class ParameterTypeMixin:
    """`parameter_type_cls` field"""

    def __post_init_post_parse__(self) -> None:
        self._parameter_type_cls: type | None = None

    @property
    def parameter_type_cls(self) -> type:
        if self._parameter_type_cls is None:
            raise ConfigInitializationException
        return self._parameter_type_cls

    @parameter_type_cls.setter
    def parameter_type_cls(self, value: type) -> None:
        self._parameter_type_cls = value

    def initialize_parameter_cls(self, package: str, typename: str, entrypoint: str) -> None:
        _logger.debug('Registering parameter type for entrypoint `%s`', entrypoint)
        entrypoint = entrypoint.lstrip('_')
        module_name = f'{package}.types.{typename}.parameter.{pascal_to_snake(entrypoint)}'
        cls_name = snake_to_pascal(entrypoint) + 'Parameter'
        self.parameter_type_cls = import_from(module_name, cls_name)


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
    source: str | ContractConfig | None = None
    destination: str | ContractConfig | None = None
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
        if self.entrypoint:
            module_name = self.destination_contract_config.module_name
            yield 'dipdup.models', 'Transaction'
            yield self.format_parameter_import(package, module_name, self.entrypoint, self.alias)
            yield self.format_storage_import(package, module_name)
        else:
            yield self.format_untyped_operation_import()

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        if self.entrypoint:
            module_name = self.destination_contract_config.module_name
            yield self.format_operation_argument(
                module_name,
                self.entrypoint,
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
    source: str | ContractConfig | None = None
    similar_to: str | ContractConfig | None = None
    originated_contract: str | ContractConfig | None = None
    optional: bool = False
    strict: bool = False
    alias: str | None = None

    def __post_init_post_parse__(self) -> None:
        super().__post_init_post_parse__()
        self._matched_originations: list[str] = []

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

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        if self.originated_contract:
            module_name = self.originated_contract_config.module_name
        elif self.similar_to:
            module_name = self.similar_to_contract_config.module_name
        elif self.source:
            yield 'dipdup.models', 'OperationData'
            return
        else:
            raise ConfigurationError(
                'Origination pattern must have at least one of `source`, `similar_to`, `originated_contract` fields'
            )

        yield 'dipdup.models', 'Origination'
        yield self.format_storage_import(package, module_name)

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        if self.originated_contract or self.similar_to:
            yield self.format_origination_argument(
                self.module_name,
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
    """Mixin for callback configs

    :param callback: Callback name
    """

    callback: str

    def __init_subclass__(cls, kind: str) -> None:
        cls._kind = kind  # type: ignore[attr-defined]

    def __post_init_post_parse__(self) -> None:
        self._callback_fn = None
        if self.callback and self.callback != pascal_to_snake(self.callback, strip_dots=False):
            raise ConfigurationError('`callback` field must be a valid Python module name')

    @cached_property
    def kind(self) -> str:
        return self._kind  # type: ignore[attr-defined,no-any-return]

    @cached_property
    def callback_fn(self) -> Callable[..., Awaitable[None]]:
        if self._callback_fn is None:
            raise ConfigInitializationException
        return self._callback_fn

    def initialize_callback_fn(self, package: str) -> None:
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


OperationHandlerPatternConfigU = OperationHandlerOriginationPatternConfig | OperationHandlerTransactionPatternConfig


@dataclass
class OperationHandlerConfig(HandlerConfig, kind='handler'):
    """Operation handler config

    :param callback: Name of method in `handlers` package
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
class TemplateValuesMixin:
    """`template_values` field"""

    def __post_init_post_parse__(self) -> None:
        self._template_values: dict[str, str] = {}

    @cached_property
    def template_values(self) -> dict[str, str]:
        return self._template_values


@dataclass
class SubscriptionsMixin:
    """`subscriptions` field"""

    def __post_init_post_parse__(self) -> None:
        self.subscriptions: set[Subscription] = set()


@dataclass
class IndexTemplateConfig(NameMixin):
    """Index template config

    :param kind: always `template`
    :param name: Name of index template
    :param template_values: Values to be substituted in template (`<key>` -> `value`)
    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing at (DipDup will terminate at this level)
    """

    kind = 'template'
    template: str
    values: dict[str, str]
    first_level: int = 0
    last_level: int = 0


@dataclass
class IndexConfig(ABC, TemplateValuesMixin, NameMixin, SubscriptionsMixin, ParentMixin['ResolvedIndexConfigU']):
    """Index config

    :param datasource: Alias of index datasource in `datasources` section
    """

    kind: str
    datasource: str | TzktDatasourceConfig

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
        """Calculate hash to ensure config has not changed since last run."""
        # FIXME: How to convert pydantic dataclass into dict without json.dumps? asdict is not recursive.
        config_json = json.dumps(self, default=pydantic_encoder)
        config_dict = json.loads(config_json)

        self.strip(config_dict)

        config_json = json.dumps(config_dict)
        return hashlib.sha256(config_json.encode()).hexdigest()

    @classmethod
    def strip(cls, config_dict: dict[str, Any]) -> None:
        """Strip config from tunables that are not needed for hash calculation."""
        config_dict['datasource'].pop('http', None)
        config_dict['datasource'].pop('buffer_size', None)

    @abstractmethod
    def import_objects(self, package: str) -> None:
        ...


@dataclass
class OperationIndexConfig(IndexConfig):
    """Operation index config

    :param kind: always `operation`
    :param handlers: List of indexer handlers
    :param types: Types of transaction to fetch
    :param contracts: Aliases of contracts being indexed in `contracts` section
    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing at (DipDup will terminate at this level)
    """

    kind: Literal['operation']
    handlers: tuple[OperationHandlerConfig, ...]
    types: tuple[OperationType, ...] = (OperationType.transaction,)
    contracts: list[str | ContractConfig] = field(default_factory=list)

    first_level: int = 0
    last_level: int = 0

    @classmethod
    def strip(cls, config_dict: dict[str, Any]) -> None:
        super().strip(config_dict)
        for handler in config_dict['handlers']:
            for item in handler['pattern']:
                item.pop('alias', None)

    @cached_property
    def entrypoint_filter(self) -> set[str | None]:
        """Set of entrypoints to filter operations with before an actual matching"""
        entrypoints = set()
        for handler_config in self.handlers:
            for pattern_config in handler_config.pattern:
                if isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
                    entrypoints.add(pattern_config.entrypoint)
        return set(entrypoints)

    @cached_property
    def address_filter(self) -> set[str]:
        """Set of addresses (any field) to filter operations with before an actual matching"""
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

    def import_objects(self, package: str) -> None:
        for handler_config in self.handlers:
            handler_config.initialize_callback_fn(package)

            for pattern_config in handler_config.pattern:
                if isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
                    if not pattern_config.entrypoint:
                        continue

                    module_name = pattern_config.destination_contract_config.module_name
                    pattern_config.initialize_parameter_cls(package, module_name, pattern_config.entrypoint)
                    pattern_config.initialize_storage_cls(package, module_name)

                elif isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
                    if not (pattern_config.originated_contract or pattern_config.similar_to):
                        continue

                    module_name = pattern_config.module_name
                    pattern_config.initialize_storage_cls(package, module_name)

                else:
                    raise NotImplementedError


@dataclass
class BigMapHandlerConfig(HandlerConfig, kind='handler'):
    """Big map handler config

    :param contract: Contract to fetch big map from
    :param path: Path to big map (alphanumeric string with dots)
    """

    contract: str | ContractConfig
    path: str

    def __post_init_post_parse__(self) -> None:
        super().__post_init_post_parse__()
        self._key_type_cls: type[Any] | None = None
        self._value_type_cls: type[Any] | None = None

    @classmethod
    def format_key_import(cls, package: str, module_name: str, path: str) -> tuple[str, str]:
        key_cls = f'{snake_to_pascal(path)}Key'
        key_module = f'{pascal_to_snake(path)}_key'
        return f'{package}.types.{module_name}.big_map.{key_module}', key_cls

    @classmethod
    def format_value_import(cls, package: str, module_name: str, path: str) -> tuple[str, str]:
        value_cls = f'{snake_to_pascal(path)}Value'
        value_module = f'{pascal_to_snake(path)}_value'
        return f'{package}.types.{module_name}.big_map.{value_module}', value_cls

    @classmethod
    def format_big_map_diff_argument(cls, path: str) -> tuple[str, str]:
        key_cls = f'{snake_to_pascal(path)}Key'
        value_cls = f'{snake_to_pascal(path)}Value'
        return pascal_to_snake(path), f'BigMapDiff[{key_cls}, {value_cls}]'

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models', 'BigMapDiff'
        yield package, 'models as models'

        yield self.format_key_import(package, self.contract_config.module_name, self.path)
        yield self.format_value_import(package, self.contract_config.module_name, self.path)

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield self.format_big_map_diff_argument(self.path)

    @cached_property
    def contract_config(self) -> ContractConfig:
        if not isinstance(self.contract, ContractConfig):
            raise ConfigInitializationException
        return self.contract

    @cached_property
    def key_type_cls(self) -> type:
        if self._key_type_cls is None:
            raise ConfigInitializationException
        return self._key_type_cls

    @cached_property
    def value_type_cls(self) -> type:
        if self._value_type_cls is None:
            raise ConfigInitializationException
        return self._value_type_cls

    def initialize_big_map_type(self, package: str) -> None:
        """Resolve imports and initialize key and value type classes"""
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
    """Big map index config

    :param kind: always `big_map`
    :param datasource: Index datasource to fetch big maps with
    :param handlers: Description of big map diff handlers
    :param skip_history: Fetch only current big map keys ignoring historical changes
    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing at (Dipdup will terminate at this level)
    """

    kind: Literal['big_map']
    datasource: str | TzktDatasourceConfig
    handlers: tuple[BigMapHandlerConfig, ...]

    skip_history: SkipHistory = SkipHistory.never

    first_level: int = 0
    last_level: int = 0

    @cached_property
    def contracts(self) -> set[ContractConfig]:
        return {handler_config.contract_config for handler_config in self.handlers}

    @classmethod
    def strip(cls, config_dict: dict[str, Any]) -> None:
        super().strip(config_dict)
        config_dict.pop('skip_history', None)

    def import_objects(self, package: str) -> None:
        for handler_config in self.handlers:
            handler_config.initialize_callback_fn(package)
            handler_config.initialize_big_map_type(package)


@dataclass
class HeadHandlerConfig(HandlerConfig, kind='handler'):
    """Head block handler config"""

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models', 'HeadBlockData'
        yield package, 'models as models'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield 'head', 'HeadBlockData'


@dataclass
class HeadIndexConfig(IndexConfig):
    """Head block index config"""

    kind: Literal['head']
    datasource: str | TzktDatasourceConfig
    handlers: tuple[HeadHandlerConfig, ...]

    @property
    def first_level(self) -> int:
        return 0

    @property
    def last_level(self) -> int:
        return 0

    def import_objects(self, package: str) -> None:
        for handler_config in self.handlers:
            handler_config.initialize_callback_fn(package)


@dataclass
class TokenTransferHandlerConfig(HandlerConfig, kind='handler'):
    contract: str | ContractConfig | None = None
    token_id: int | None = None
    from_: str | ContractConfig | None = Field(default=None, alias='from')
    to: str | ContractConfig | None = None

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models', 'TokenTransferData'
        yield package, 'models as models'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield 'token_transfer', 'TokenTransferData'


@dataclass
class TokenTransferIndexConfig(IndexConfig):
    """Token index config"""

    kind: Literal['token_transfer']
    datasource: str | TzktDatasourceConfig
    handlers: tuple[TokenTransferHandlerConfig, ...] = field(default_factory=tuple)

    first_level: int = 0
    last_level: int = 0

    def import_objects(self, package: str) -> None:
        for handler_config in self.handlers:
            handler_config.initialize_callback_fn(package)


@dataclass
class EventHandlerConfig(HandlerConfig, kind='handler'):
    contract: str | ContractConfig
    tag: str

    def __post_init_post_parse__(self) -> None:
        super().__post_init_post_parse__()
        self._event_type_cls: type[Any] | None = None

    @cached_property
    def contract_config(self) -> ContractConfig:
        if not isinstance(self.contract, ContractConfig):
            raise ConfigInitializationException
        return self.contract

    @cached_property
    def event_type_cls(self) -> type:
        if self._event_type_cls is None:
            raise ConfigInitializationException
        return self._event_type_cls

    def initialize_event_type(self, package: str) -> None:
        """Resolve imports and initialize key and value type classes"""
        _logger.debug('Registering event types for tag `%s`', self.tag)
        tag = pascal_to_snake(self.tag.replace('.', '_'))

        module_name = f'{package}.types.{self.contract_config.module_name}.event.{tag}'
        cls_name = snake_to_pascal(f'{tag}_payload')
        self._event_type_cls = import_from(module_name, cls_name)

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models', 'Event'
        yield package, 'models as models'

        event_cls = snake_to_pascal(self.tag + '_payload')
        event_module = pascal_to_snake(self.tag)
        module_name = self.contract_config.module_name
        yield f'{package}.types.{module_name}.event.{event_module}', event_cls

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        event_cls = snake_to_pascal(self.tag + '_payload')
        yield 'ctx', 'HandlerContext'
        yield 'event', f'Event[{event_cls}]'


@dataclass
class UnknownEventHandlerConfig(HandlerConfig, kind='handler'):
    contract: str | ContractConfig

    @cached_property
    def contract_config(self) -> ContractConfig:
        if not isinstance(self.contract, ContractConfig):
            raise ConfigInitializationException
        return self.contract

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models', 'UnknownEvent'
        yield package, 'models as models'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield 'event', 'UnknownEvent'


EventHandlerConfigU = EventHandlerConfig | UnknownEventHandlerConfig


@dataclass
class EventIndexConfig(IndexConfig):
    kind: Literal['event']
    datasource: str | TzktDatasourceConfig
    handlers: tuple[EventHandlerConfigU, ...] = field(default_factory=tuple)

    first_level: int = 0
    last_level: int = 0

    def import_objects(self, package: str) -> None:
        for handler_config in self.handlers:
            handler_config.initialize_callback_fn(package)

            if isinstance(handler_config, EventHandlerConfig):
                handler_config.initialize_event_type(package)


ResolvedIndexConfigU = (
    OperationIndexConfig | BigMapIndexConfig | HeadIndexConfig | TokenTransferIndexConfig | EventIndexConfig
)
IndexConfigU = ResolvedIndexConfigU | IndexTemplateConfig
HandlerPatternConfigU = OperationHandlerOriginationPatternConfig | OperationHandlerTransactionPatternConfig


@dataclass
class HasuraConfig:
    """Config for the Hasura integration.

    :param url: URL of the Hasura instance.
    :param admin_secret: Admin secret of the Hasura instance.
    :param create_source: Whether source should be added to Hasura if missing.
    :param source: Hasura source for DipDup to configure, others will be left untouched.
    :param select_limit: Row limit for unauthenticated queries.
    :param allow_aggregations: Whether to allow aggregations in unauthenticated queries.
    :param camel_case: Whether to use camelCase instead of default pascal_case for the field names (incompatible with `metadata_interface` flag)
    :param rest: Enable REST API both for autogenerated and custom queries.
    :param http: HTTP connection tunables
    """

    url: str
    admin_secret: str | None = field(default=None, repr=False)
    create_source: bool = False
    source: str = 'default'
    select_limit: int = 100
    allow_aggregations: bool = True
    camel_case: bool = False
    rest: bool = True
    http: HTTPConfig | None = None

    @validator('url', allow_reuse=True)
    def _valid_url(cls, v: str) -> str:
        parsed_url = urlparse(v)
        if not (parsed_url.scheme and parsed_url.netloc):
            raise ConfigurationError(f'`{v}` is not a valid Hasura URL')
        return v.rstrip('/')

    @cached_property
    def headers(self) -> dict[str, str]:
        """Headers to include with every request"""
        if self.admin_secret:
            return {'X-Hasura-Admin-Secret': self.admin_secret}
        return {}


@dataclass
class JobConfig(NameMixin):
    """Job schedule config

    :param hook: Name of hook to run
    :param crontab: Schedule with crontab syntax (`* * * * *`)
    :param interval: Schedule with interval in seconds
    :param daemon: Run hook as a daemon (never stops)
    :param args: Arguments to pass to the hook
    """

    hook: str | HookConfig
    crontab: str | None = None
    interval: int | None = None
    daemon: bool = False
    args: dict[str, Any] = field(default_factory=dict)

    def __post_init_post_parse__(self) -> None:
        schedules_enabled = sum(int(bool(x)) for x in (self.crontab, self.interval, self.daemon))
        if schedules_enabled > 1:
            raise ConfigurationError('Only one of `crontab`, `interval` of `daemon` can be specified')
        elif not schedules_enabled:
            raise ConfigurationError('One of `crontab`, `interval` or `daemon` must be specified')

        NameMixin.__post_init_post_parse__(self)

    @cached_property
    def hook_config(self) -> HookConfig:
        if not isinstance(self.hook, HookConfig):
            raise ConfigInitializationException
        return self.hook


@dataclass
class SentryConfig:
    """Config for Sentry integration.

    :param dsn: DSN of the Sentry instance
    :param environment: Environment; if not set, guessed from docker/ci/gha/local.
    :param server_name: Server name; defaults to obfuscated hostname.
    :param release: Release version; defaults to DipDup package version.
    :param user_id: User ID; defaults to obfuscated package/environment.
    :param debug: Catch warning messages, increase verbosity.
    """

    dsn: str = ''
    environment: str | None = None
    server_name: str | None = None
    release: str | None = None
    user_id: str | None = None
    debug: bool = False


@dataclass
class PrometheusConfig:
    """Config for Prometheus integration.

    :param host: Host to bind to
    :param port: Port to bind to
    :param update_interval: Interval to update some metrics in seconds
    """

    host: str
    port: int = 8000
    update_interval: float = 1.0


@dataclass
class HookConfig(CallbackMixin, kind='hook'):
    """Hook config

    :param args: Mapping of argument names and annotations (checked lazily when possible)
    :param atomic: Wrap hook in a single database transaction
    """

    args: dict[str, str] = field(default_factory=dict)
    atomic: bool = False

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HookContext'
        for name, annotation in self.args.items():
            yield name, annotation.split('.')[-1]

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HookContext'
        for _, annotation in self.args.items():
            with suppress(ValueError):
                package, obj = annotation.rsplit('.', 1)
                yield package, obj


@dataclass
class EventHookConfig(HookConfig, kind='hook'):
    pass


event_hooks = {
    # NOTE: Fires on every run after datasources and schema are initialized.
    # NOTE: Default: nothing.
    'on_restart': EventHookConfig(
        callback='on_restart',
    ),
    # NOTE: Fires on rollback which affects specific index and can't be processed unattended.
    # NOTE: Default: database rollback.
    'on_index_rollback': EventHookConfig(
        callback='on_index_rollback',
        args={
            'index': 'dipdup.index.Index',
            'from_level': 'int',
            'to_level': 'int',
        },
    ),
    # NOTE: Fires when DipDup runs with empty schema, right after schema is initialized.
    # NOTE: Default: nothing.
    'on_reindex': EventHookConfig(
        callback='on_reindex',
    ),
    # NOTE: Fires when all indexes reach REALTIME state.
    # NOTE: Default: nothing.
    'on_synchronized': EventHookConfig(
        callback='on_synchronized',
    ),
}


@dataclass
class AdvancedConfig:
    """Feature flags and other advanced config.

    :param reindex: Mapping of reindexing reasons and actions DipDup performs
    :param scheduler: `apscheduler` scheduler config
    :param postpone_jobs: Do not start job scheduler until all indexes are in realtime state
    :param early_realtime: Establish realtime connection immediately after startup
    :param merge_subscriptions: Subscribe to all operations instead of exact channels
    :param metadata_interface: Expose metadata interface for TzKT
    :param skip_version_check: Do not check for new DipDup versions on startup
    :param rollback_depth: A number of levels to keep for rollback
    :param crash_reporting: Enable crash reporting
    """

    reindex: dict[ReindexingReason, ReindexingAction] = field(default_factory=dict)
    scheduler: dict[str, Any] | None = None
    postpone_jobs: bool = False
    early_realtime: bool = False
    merge_subscriptions: bool = False
    metadata_interface: bool = False
    skip_version_check: bool = False
    rollback_depth: int = 2
    crash_reporting: bool = False


@dataclass
class DipDupConfig:
    """Main indexer config

    :param spec_version: Version of specification
    :param package: Name of indexer's Python package, existing or not
    :param datasources: Mapping of datasource aliases and datasource configs
    :param database: Database config
    :param contracts: Mapping of contract aliases and contract configs
    :param indexes: Mapping of index aliases and index configs
    :param templates: Mapping of template aliases and index templates
    :param jobs: Mapping of job aliases and job configs
    :param hooks: Mapping of hook aliases and hook configs
    :param hasura: Hasura integration config
    :param sentry: Sentry integration config
    :param prometheus: Prometheus integration config
    :param advanced: Advanced config
    :param custom: User-defined Custom config
    """

    spec_version: str
    package: str
    datasources: dict[str, DatasourceConfigU] = field(default_factory=dict)
    database: SqliteDatabaseConfig | PostgresDatabaseConfig = SqliteDatabaseConfig(kind='sqlite')
    contracts: dict[str, ContractConfig] = field(default_factory=dict)
    indexes: dict[str, IndexConfigU] = field(default_factory=dict)
    templates: dict[str, ResolvedIndexConfigU] = field(default_factory=dict)
    jobs: dict[str, JobConfig] = field(default_factory=dict)
    hooks: dict[str, HookConfig] = field(default_factory=dict)
    hasura: HasuraConfig | None = None
    sentry: SentryConfig | None = None
    prometheus: PrometheusConfig | None = None
    advanced: AdvancedConfig = AdvancedConfig()
    custom: dict[str, Any] = field(default_factory=dict)
    logging: LoggingValues = LoggingValues.default

    def __post_init_post_parse__(self) -> None:
        if self.package != pascal_to_snake(self.package):
            # TODO: Remove in 7.0
            # raise ConfigurationError('Python package name must be in snake_case.')
            _logger.warning('Python package name must be in snake_case.')

        self.paths: list[Path] = []
        self.environment: dict[str, str] = {}
        self._callback_patterns: dict[str, list[Sequence[HandlerPatternConfigU]]] = defaultdict(list)
        self._contract_addresses = {contract.address for contract in self.contracts.values()}

    @cached_property
    def schema_name(self) -> str:
        if isinstance(self.database, PostgresDatabaseConfig):
            return self.database.schema_name
        # NOTE: Not exactly correct; historical reason
        return DEFAULT_POSTGRES_SCHEMA

    @cached_property
    def package_path(self) -> Path:
        """Absolute path to the indexer package, existing or default"""
        # NOTE: Integration tests run in isolated environment
        if is_in_tests():
            return Path.cwd() / self.package

        with suppress(ImportError):
            package = importlib.import_module(self.package)
            if package.__file__ is None:
                raise RuntimeError(f'`{package.__name__}` package has no `__file__` attribute')
            return Path(package.__file__).parent

        # NOTE: Detect src/<package> layout
        if Path('src').is_dir():
            return Path('src', self.package)

        return Path(self.package)

    @property
    def oneshot(self) -> bool:
        """Whether all indexes have `last_level` field set"""
        syncable_indexes = tuple(c for c in self.indexes.values() if not isinstance(c, HeadIndexConfig))
        oneshot_indexes = tuple(c for c in syncable_indexes if c.last_level)
        if len(oneshot_indexes) == len(syncable_indexes) > 0:
            return True
        return False

    @classmethod
    def load(
        cls,
        paths: list[Path],
        environment: bool = True,
    ) -> DipDupConfig:
        # NOTE: __future__.annotations
        JobConfig.__pydantic_model__.update_forward_refs()  # type: ignore[attr-defined]

        yaml = YAML(typ='base')

        json_config: dict[str, Any] = {}
        config_environment: dict[str, str] = {}
        for path in paths:
            raw_config = cls._load_raw_config(path)

            if environment:
                raw_config, raw_config_environment = cls._substitute_env_variables(raw_config)
                config_environment.update(raw_config_environment)

            json_config.update(yaml.load(raw_config))

        try:
            config = cls(**json_config)
        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(str(e)) from e

        config.environment = config_environment
        config.paths = paths
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

    def get_datasource(self, name: str) -> DatasourceConfigU:
        try:
            return self.datasources[name]
        except KeyError as e:
            raise ConfigurationError(f'Datasource `{name}` not found in `datasources` config section') from e

    def get_index(self, name: str) -> IndexConfigU:
        try:
            return self.indexes[name]
        except KeyError as e:
            raise ConfigurationError(f'Index `{name}` not found in `indexes` config section') from e

    def get_template(self, name: str) -> ResolvedIndexConfigU:
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

    def set_up_logging(self) -> None:
        level = {
            LoggingValues.default: logging.INFO,
            LoggingValues.quiet: logging.WARNING,
            LoggingValues.verbose: logging.DEBUG,
        }[self.logging]
        logging.getLogger('dipdup').setLevel(level)
        # NOTE: Hack for some mocked tests
        if isinstance(self.package, str):
            logging.getLogger(self.package).setLevel(level)

    def initialize(self, skip_imports: bool = False) -> None:
        self._set_names()
        self._resolve_templates()
        self._resolve_links()
        self._validate()

        if skip_imports:
            return

        for index_config in self.indexes.values():
            if isinstance(index_config, IndexTemplateConfig):
                raise ConfigInitializationException
            index_config.import_objects(self.package)

    def add_index(self, name: str, template: str, values: dict[str, str]) -> None:
        if name in self.indexes:
            raise IndexAlreadyExistsError(self, name)
        template_config = IndexTemplateConfig(
            template=template,
            values=values,
        )
        template_config.name = name
        self._resolve_template(template_config)
        index_config = cast(ResolvedIndexConfigU, self.indexes[name])
        self._resolve_index_links(index_config)
        self._resolve_index_subscriptions(index_config)
        index_config.name = name
        index_config.import_objects(self.package)

    @classmethod
    def _load_raw_config(cls, path: Path) -> str:
        _logger.debug('Loading config from %s', path)
        try:
            with open(path) as file:
                return ''.join(filter(cls._filter_commented_lines, file.readlines()))
        except OSError as e:
            raise ConfigurationError(str(e)) from e

    @classmethod
    def _filter_commented_lines(cls, line: str) -> bool:
        return '#' not in line or line.lstrip()[0] != '#'

    @classmethod
    def _substitute_env_variables(cls, raw_config: str) -> tuple[str, dict[str, str]]:
        _logger.debug('Substituting environment variables')
        environment: dict[str, str] = {}

        for match in re.finditer(ENV_VARIABLE_REGEX, raw_config):
            variable, default_value = match.group('var_name'), match.group('default_value')
            value = env.get(variable, default_value)
            if not value:
                raise ConfigurationError(f'Environment variable `{variable}` is not set')
            environment[variable] = value
            placeholder = match.group(0)
            raw_config = raw_config.replace(placeholder, value or default_value)

        return raw_config, environment

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

        # NOTE: Hook names and callbacks
        for name, hook_config in self.hooks.items():
            if name != hook_config.callback:
                raise ConfigurationError(f'`{name}` hook name must be equal to `callback` value.')
            if name in event_hooks:
                raise ConfigurationError(f'`{name}` hook name is reserved by event hook')

        # NOTE: Conflicting rollback techniques
        for name, datasource_config in self.datasources.items():
            if not isinstance(datasource_config, TzktDatasourceConfig):
                continue
            if datasource_config.buffer_size and self.advanced.rollback_depth:
                raise ConfigurationError(
                    f'`{name}`: `buffer_size` option is incompatible with `advanced.rollback_depth`'
                )

    def _resolve_template(self, template_config: IndexTemplateConfig) -> None:
        _logger.debug('Resolving index config `%s` from template `%s`', template_config.name, template_config.template)

        template = self.get_template(template_config.template)
        raw_template = json.dumps(template, default=pydantic_encoder)
        for key, value in template_config.values.items():
            value_regex = r'<[ ]*' + key + r'[ ]*>'
            raw_template = re.sub(value_regex, value, raw_template)

        if missing_value := re.search(r'<*>', raw_template):
            raise ConfigurationError(
                f'`{template_config.name}` index config is missing required template value `{missing_value}`'
            )

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
        for index_config in self.indexes.values():
            if isinstance(index_config, IndexTemplateConfig):
                raise ConfigInitializationException('Index templates must be resolved first')

            self._resolve_index_links(index_config)
            # TODO: Not exactly link resolving, move somewhere else
            self._resolve_index_subscriptions(index_config)

        for job_config in self.jobs.values():
            if isinstance(job_config.hook, str):
                hook_config = self.get_hook(job_config.hook)
                if job_config.daemon and hook_config.atomic:
                    raise ConfigurationError('`HookConfig.atomic` and `JobConfig.daemon` flags are mutually exclusive')
                job_config.hook = hook_config

    def _resolve_index_subscriptions(self, index_config: IndexConfigU) -> None:
        if isinstance(index_config, IndexTemplateConfig):
            return
        if index_config.subscriptions:
            return

        if isinstance(index_config, OperationIndexConfig):
            if OperationType.transaction in index_config.types:
                if self.advanced.merge_subscriptions:
                    index_config.subscriptions.add(TransactionSubscription())
                else:
                    for contract_config in index_config.contracts:
                        if not isinstance(contract_config, ContractConfig):
                            raise ConfigInitializationException
                        index_config.subscriptions.add(TransactionSubscription(address=contract_config.address))

            if OperationType.origination in index_config.types:
                index_config.subscriptions.add(OriginationSubscription())

        elif isinstance(index_config, BigMapIndexConfig):
            if self.advanced.merge_subscriptions:
                index_config.subscriptions.add(BigMapSubscription())
            else:
                for big_map_handler_config in index_config.handlers:
                    address, path = big_map_handler_config.contract_config.address, big_map_handler_config.path
                    index_config.subscriptions.add(BigMapSubscription(address=address, path=path))

        elif isinstance(index_config, HeadIndexConfig):
            index_config.subscriptions.add(HeadSubscription())

        elif isinstance(index_config, TokenTransferIndexConfig):
            if self.advanced.merge_subscriptions:
                index_config.subscriptions.add(TokenTransferSubscription())
            else:
                for handler_config in index_config.handlers:
                    contract = (
                        handler_config.contract.address if isinstance(handler_config.contract, ContractConfig) else None
                    )
                    from_ = handler_config.from_.address if isinstance(handler_config.from_, ContractConfig) else None
                    to = handler_config.to.address if isinstance(handler_config.to, ContractConfig) else None
                    index_config.subscriptions.add(
                        TokenTransferSubscription(
                            contract=contract, from_=from_, to=to, token_id=handler_config.token_id
                        )
                    )

        elif isinstance(index_config, EventIndexConfig):
            if self.advanced.merge_subscriptions:
                index_config.subscriptions.add(EventSubscription())
            else:
                for event_handler_config in index_config.handlers:
                    address = event_handler_config.contract_config.address
                    index_config.subscriptions.add(EventSubscription(address=address))

        else:
            raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

        if not index_config.subscriptions:
            raise ConfigurationError(
                f'`{index_config.name}` index has no subscriptions; ensure that config is correct.'
            )

    def _resolve_index_links(self, index_config: ResolvedIndexConfigU) -> None:
        """Resolve contract and datasource configs by aliases"""
        # NOTE: Each index must have a corresponding (currently) TzKT datasource
        if isinstance(index_config.datasource, str):
            index_config.datasource = self.get_tzkt_datasource(index_config.datasource)

        if isinstance(index_config, OperationIndexConfig):
            if index_config.contracts is not None:
                for i, contract in enumerate(index_config.contracts):
                    if isinstance(contract, str):
                        index_config.contracts[i] = self.get_contract(contract)

            for handler_config in index_config.handlers:
                handler_config.parent = index_config
                self._callback_patterns[handler_config.callback].append(handler_config.pattern)
                for idx, pattern_config in enumerate(handler_config.pattern):
                    # NOTE: Untyped operations are named as `transaction_N` or `origination_N` based on their index
                    pattern_config._subgroup_index = idx

                    if isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
                        if isinstance(pattern_config.destination, str):
                            pattern_config.destination = self.get_contract(pattern_config.destination)
                        if isinstance(pattern_config.source, str):
                            pattern_config.source = self.get_contract(pattern_config.source)

                    elif isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
                        if isinstance(pattern_config.source, str):
                            pattern_config.source = self.get_contract(pattern_config.source)
                        if isinstance(pattern_config.similar_to, str):
                            pattern_config.similar_to = self.get_contract(pattern_config.similar_to)
                        if isinstance(pattern_config.originated_contract, str):
                            pattern_config.originated_contract = self.get_contract(pattern_config.originated_contract)

        elif isinstance(index_config, BigMapIndexConfig):
            for handler in index_config.handlers:
                handler.parent = index_config
                # TODO: Verify callback uniqueness
                # self._callback_patterns[handler.callback].append(handler.pattern)
                if isinstance(handler.contract, str):
                    handler.contract = self.get_contract(handler.contract)

        elif isinstance(index_config, HeadIndexConfig):
            for head_handler_config in index_config.handlers:
                head_handler_config.parent = index_config

        elif isinstance(index_config, TokenTransferIndexConfig):
            for token_transfer_handler_config in index_config.handlers:
                token_transfer_handler_config.parent = index_config

                if isinstance(token_transfer_handler_config.contract, str):
                    token_transfer_handler_config.contract = self.get_contract(token_transfer_handler_config.contract)

        elif isinstance(index_config, EventIndexConfig):
            for event_handler_config in index_config.handlers:
                event_handler_config.parent = index_config

                if isinstance(event_handler_config.contract, str):
                    event_handler_config.contract = self.get_contract(event_handler_config.contract)

        else:
            raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

    def _set_names(self) -> None:
        # TODO: Forbid reusing names between sections?
        named_config_sections = cast(
            tuple[dict[str, NameMixin], ...],
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
