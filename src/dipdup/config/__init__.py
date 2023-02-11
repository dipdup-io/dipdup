"""Config files parsing and processing

As you can see from the amount of code below, lots of things are going on here:

* Templating indexes and env variables (`<...>` and `${...}` syntax)
* Config initialization and validation
* Methods to generate paths for codegen
* And even importing contract types on demand

* YAML (de)serialization moved to `dipdup.yaml` module.

Dataclasses are used in this module instead of BaseModel for historical reasons, thus "...Mixin" classes to workaround the lack of proper
inheritance.
"""
from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import logging.config
import re
import sys
from abc import ABC
from abc import abstractmethod
from collections import Counter
from contextlib import suppress
from dataclasses import field
from pathlib import Path
from pydoc import locate
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Generic
from typing import Iterator
from typing import Literal
from typing import TypeVar
from typing import cast
from urllib.parse import quote_plus
from urllib.parse import urlparse

from pydantic import validator
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder

from dipdup import baking_bad
from dipdup import env
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import FrameworkException
from dipdup.exceptions import IndexAlreadyExistsError
from dipdup.models import LoggingValues
from dipdup.models import ReindexingAction
from dipdup.models import ReindexingReason
from dipdup.models.tezos_tzkt import TzktOperationType
from dipdup.subscriptions import Subscription
from dipdup.utils import import_from
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal
from dipdup.yaml import DipDupYAMLConfig

DEFAULT_IPFS_URL = 'https://ipfs.io/ipfs'
DEFAULT_TZKT_URL = str(next(iter(baking_bad.TZKT_API_URLS.keys())))
DEFAULT_POSTGRES_SCHEMA = 'public'
DEFAULT_POSTGRES_DATABASE = 'postgres'
DEFAULT_POSTGRES_USER = 'postgres'
DEFAULT_POSTGRES_PORT = 5432
DEFAULT_SQLITE_PATH = ':memory:'

TEZOS_ADDRESS_PREFIXES = (
    'KT1',
    # NOTE: Wallet addresses are allowed during config validation for debugging purposes.
    # NOTE: It's a undocumented hack to filter by `source` field. Wallet indexing is not supported.
    # NOTE: See https://github.com/dipdup-io/dipdup/issues/291
    'tz1',
    'tz2',
    'tz3',
)
TEZOS_ADDRESS_LENGTH = 36
ETH_ADDRESS_PREFIXES = ('0x',)
ETH_ADDRESS_LENGTH = 42


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

    @property
    def connection_string(self) -> str:
        # NOTE: `maxsize=1` is important! Concurrency will be broken otherwise.
        # NOTE: https://github.com/tortoise/tortoise-orm/issues/792
        connection_string = (
            f'{self.kind}://{self.user}:{quote_plus(self.password)}@{self.host}:{self.port}/{self.database}?maxsize=1'
        )
        if self.schema_name != DEFAULT_POSTGRES_SCHEMA:
            connection_string += f'&schema={self.schema_name}'
        return connection_string

    @property
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
class HttpConfig:
    """Advanced configuration of HTTP client

    :param retry_count: Number of retries after request failed before giving up
    :param retry_sleep: Sleep time between retries
    :param retry_multiplier: Multiplier for sleep time between retries
    :param ratelimit_rate: Number of requests per period ("drops" in leaky bucket)
    :param ratelimit_period: Time period for rate limiting in seconds
    :param ratelimit_sleep: Sleep time between requests when rate limit is reached
    :param connection_limit: Number of simultaneous connections
    :param connection_timeout: Connection timeout in seconds
    :param batch_size: Number of items fetched in a single paginated request (for some APIs)
    :param replay_path: Development-only option to use cached HTTP responses instead of making real requests
    """

    retry_count: int | None = None
    retry_sleep: float | None = None
    retry_multiplier: float | None = None
    ratelimit_rate: int | None = None
    ratelimit_period: int | None = None
    ratelimit_sleep: float | None = None
    connection_limit: int | None = None
    connection_timeout: int | None = None
    batch_size: int | None = None
    replay_path: str | None = None


@dataclass
class ResolvedHttpConfig:
    """HTTP client configuration with defaults"""

    retry_count: int = sys.maxsize
    retry_sleep: float = 0.0
    retry_multiplier: float = 1.0
    ratelimit_rate: int = 0
    ratelimit_period: int = 0
    ratelimit_sleep: float = 5.0
    connection_limit: int = 100
    connection_timeout: int = 60
    batch_size: int = 1000
    replay_path: str | None = None

    @classmethod
    def create(
        cls,
        default: HttpConfig,
        user: HttpConfig | None,
    ) -> 'ResolvedHttpConfig':
        config = cls()
        # NOTE: Apply datasource defaults first
        for merge_config in (default, user):
            if merge_config is None:
                continue
            for k, v in merge_config.__dict__.items():
                if v is not None:
                    setattr(config, k, v)
        return config


@dataclass
class NameMixin:
    def __post_init_post_parse__(self) -> None:
        self._name: str | None = None

    @property
    def name(self) -> str:
        if self._name is None:
            raise ConfigInitializationException(f'{self.__class__.__name__} name is not set')
        return self._name


@dataclass
class ContractConfig(NameMixin):
    """Contract config

    :param address: Contract address
    :param code_hash: Contract code hash or address to fetch it from
    :param typename: User-defined alias for the contract script
    """

    address: str | None = None
    code_hash: int | str | None = None
    typename: str | None = None

    @property
    def module_name(self) -> str:
        return self.typename or self.name

    @validator('address', allow_reuse=True)
    def _valid_address(cls, v: str | None) -> str | None:
        # NOTE: Environment substitution was disabled during export, skip validation
        if not v or '$' in v:
            return v

        if v.startswith(TEZOS_ADDRESS_PREFIXES):
            if len(v) != TEZOS_ADDRESS_LENGTH:
                raise ConfigurationError(f'`{v}` is not a valid Tezos address')
        elif v.startswith(ETH_ADDRESS_PREFIXES):
            if len(v) != ETH_ADDRESS_LENGTH:
                raise ConfigurationError(f'`{v}` is not a valid Ethereum address')
        else:
            raise ConfigurationError(f'`{v}` is not a valid address')

        return v

    def get_address(self) -> str:
        if self.address is None:
            raise ConfigurationError(f'`contracts.{self.name}`: `address` field is required`')
        return self.address


class DatasourceConfig(ABC, NameMixin):
    kind: str
    url: str
    http: HttpConfig | None

    # TODO: Pick refactoring from `ref/config-module`
    @abstractmethod
    def __hash__(self) -> int:
        ...


class AbiDatasourceConfig(DatasourceConfig):
    ...


class IndexDatasourceConfig(DatasourceConfig):
    ...


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


@dataclass
class StorageTypeMixin:
    """`storage_type_cls` field"""

    def __post_init_post_parse__(self) -> None:
        self._storage_type_cls: type[Any] | None = None

    @property
    def storage_type_cls(self) -> type[Any]:
        if self._storage_type_cls is None:
            raise ConfigInitializationException
        return self._storage_type_cls

    def initialize_storage_cls(self, package: str, module_name: str) -> None:
        _logger.debug('Registering `%s` storage type', module_name)
        cls_name = snake_to_pascal(module_name) + 'Storage'
        module_name = f'{package}.types.{module_name}.storage'
        self._storage_type_cls = import_from(module_name, cls_name)


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

    @property
    def kind(self) -> str:
        return self._kind  # type: ignore[attr-defined,no-any-return]

    @property
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
        self._callback_fn = import_from(module_name, fn_name)


@dataclass
class HandlerConfig(CallbackMixin, ParentMixin['IndexConfig'], kind='handler'):
    def __post_init_post_parse__(self) -> None:
        CallbackMixin.__post_init_post_parse__(self)
        ParentMixin.__post_init_post_parse__(self)


@dataclass
class TemplateValuesMixin:
    """`template_values` field"""

    def __post_init_post_parse__(self) -> None:
        self._template_values: dict[str, str] = {}

    @property
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
    :param values: Values to be substituted in template (`<key>` -> `value`)
    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing at
    :param template: Template alias in `templates` section

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
    datasource: DatasourceConfig

    def __post_init_post_parse__(self) -> None:
        TemplateValuesMixin.__post_init_post_parse__(self)
        NameMixin.__post_init_post_parse__(self)
        SubscriptionsMixin.__post_init_post_parse__(self)
        ParentMixin.__post_init_post_parse__(self)

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
class HasuraConfig:
    """Config for the Hasura integration.

    :param url: URL of the Hasura instance.
    :param admin_secret: Admin secret of the Hasura instance.
    :param create_source: Whether source should be added to Hasura if missing.
    :param source: Hasura source for DipDup to configure, others will be left untouched.
    :param select_limit: Row limit for unauthenticated queries.
    :param allow_aggregations: Whether to allow aggregations in unauthenticated queries.
    :param allow_inconsistent_metadata: Whether to ignore errors when applying Hasura metadata.
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
    allow_inconsistent_metadata: bool = False
    camel_case: bool = False
    rest: bool = True
    http: HttpConfig | None = None

    @validator('url', allow_reuse=True)
    def _valid_url(cls, v: str) -> str:
        parsed_url = urlparse(v)
        if not (parsed_url.scheme and parsed_url.netloc):
            raise ConfigurationError(f'`{v}` is not a valid Hasura URL')
        return v.rstrip('/')

    @property
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

    hook: HookConfig = field()
    args: dict[str, Any] = field(default_factory=dict)
    crontab: str | None = None
    interval: int | None = None
    daemon: bool = False

    def __post_init_post_parse__(self) -> None:
        schedules_enabled = sum(int(bool(x)) for x in (self.crontab, self.interval, self.daemon))
        if schedules_enabled > 1:
            raise ConfigurationError('Only one of `crontab`, `interval` of `daemon` can be specified')
        elif not schedules_enabled:
            raise ConfigurationError('One of `crontab`, `interval` or `daemon` must be specified')

        NameMixin.__post_init_post_parse__(self)


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
    :param callback: Callback name
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
    :param metadata_interface: Expose metadata interface for TzKT
    :param skip_version_check: Do not check for new DipDup versions on startup
    :param rollback_depth: A number of levels to keep for rollback
    :param crash_reporting: Enable crash reporting
    """

    reindex: dict[ReindexingReason, ReindexingAction] = field(default_factory=dict)
    scheduler: dict[str, Any] | None = None
    postpone_jobs: bool = False
    early_realtime: bool = False
    metadata_interface: bool = False
    skip_version_check: bool = False
    rollback_depth: int = 2
    crash_reporting: bool = False


@dataclass
class DipDupConfig:
    """Main indexer config

    :param spec_version: Version of config specification, currently always `1.2`
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
    :param custom: User-defined configuration to use in callbacks
    :param logging: Modify logging verbosity
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
    sentry: SentryConfig = SentryConfig()
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
        self.json = DipDupYAMLConfig()
        self._contract_addresses = {v.address: k for k, v in self.contracts.items() if v.address is not None}
        self._contract_code_hashes = {v.code_hash: k for k, v in self.contracts.items() if v.code_hash is not None}

    @property
    def schema_name(self) -> str:
        if isinstance(self.database, PostgresDatabaseConfig):
            return self.database.schema_name
        # NOTE: Not exactly correct; historical reason
        return DEFAULT_POSTGRES_SCHEMA

    @property
    def package_path(self) -> Path:
        return env.get_package_path(self.package)

    @property
    def oneshot(self) -> bool:
        """Whether all indexes have `last_level` field set"""
        syncable_indexes = tuple(c for c in self.indexes.values() if not isinstance(c, TzktHeadIndexConfig))
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
        config_json, config_environment = DipDupYAMLConfig.load(paths, environment)

        try:
            config = cls(**config_json)
        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(str(e)) from e

        config.paths = paths
        config.json = config_json
        config.environment = config_environment
        return config

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

    def get_subsquid_datasource(self, name: str) -> SubsquidDatasourceConfig:
        datasource = self.get_datasource(name)
        if not isinstance(datasource, SubsquidDatasourceConfig):
            raise ConfigurationError('`datasource` field must refer to Subsquid datasource')
        return datasource

    def set_up_logging(self) -> None:
        level = {
            LoggingValues.default: logging.INFO,
            LoggingValues.quiet: logging.WARNING,
            LoggingValues.verbose: logging.DEBUG,
        }[self.logging]
        logging.getLogger('dipdup').setLevel(level)
        # FIXME: Hack for some mocked tests; possibly outdated
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

    def dump(self) -> str:
        return DipDupYAMLConfig.dump(self.json)

    def add_index(
        self,
        name: str,
        template: str,
        values: dict[str, str],
        first_level: int = 0,
        last_level: int = 0,
    ) -> None:
        if name in self.indexes:
            raise IndexAlreadyExistsError(name)
        template_config = IndexTemplateConfig(
            template=template,
            values=values,
            first_level=first_level,
            last_level=last_level,
        )
        template_config._name = name
        self._resolve_template(template_config)
        index_config = cast(ResolvedIndexConfigU, self.indexes[name])
        self._resolve_index_links(index_config)
        self._resolve_index_subscriptions(index_config)
        index_config._name = name
        index_config.import_objects(self.package)

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
        new_index_config._template_values = template_config.values
        new_index_config.parent = template
        new_index_config._name = template_config.name
        if not isinstance(new_index_config, TzktHeadIndexConfig):
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

        from dipdup.models.tezos_tzkt import BigMapSubscription
        from dipdup.models.tezos_tzkt import EventSubscription
        from dipdup.models.tezos_tzkt import HeadSubscription
        from dipdup.models.tezos_tzkt import OriginationSubscription
        from dipdup.models.tezos_tzkt import TokenTransferSubscription
        from dipdup.models.tezos_tzkt import TransactionSubscription

        index_config.subscriptions.add(HeadSubscription())

        if isinstance(index_config, TzktOperationsIndexConfig):
            if TzktOperationType.transaction in index_config.types:
                if index_config.datasource.merge_subscriptions:
                    index_config.subscriptions.add(TransactionSubscription())
                else:
                    for contract_config in index_config.contracts:
                        if not isinstance(contract_config, ContractConfig):
                            raise ConfigInitializationException
                        index_config.subscriptions.add(TransactionSubscription(address=contract_config.address))

            if TzktOperationType.origination in index_config.types:
                index_config.subscriptions.add(OriginationSubscription())

        elif isinstance(index_config, TzktBigMapsIndexConfig):
            if index_config.datasource.merge_subscriptions:
                index_config.subscriptions.add(BigMapSubscription())
            else:
                for big_map_handler_config in index_config.handlers:
                    address, path = big_map_handler_config.contract.address, big_map_handler_config.path
                    index_config.subscriptions.add(BigMapSubscription(address=address, path=path))

        elif isinstance(index_config, TzktHeadIndexConfig):
            index_config.subscriptions.add(HeadSubscription())

        elif isinstance(index_config, TzktTokenTransfersIndexConfig):
            if index_config.datasource.merge_subscriptions:
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

        elif isinstance(index_config, TzktOperationsUnfilteredIndexConfig):
            index_config.subscriptions.add(TransactionSubscription())

        elif isinstance(index_config, TzktEventsIndexConfig):
            if index_config.datasource.merge_subscriptions:
                index_config.subscriptions.add(EventSubscription())
            else:
                for event_handler_config in index_config.handlers:
                    address = event_handler_config.contract.address
                    index_config.subscriptions.add(EventSubscription(address=address))

        elif isinstance(index_config, EvmSubsquidEventsIndexConfig):
            ...

        elif isinstance(index_config, EvmSubsquidOperationsIndexConfig):
            ...

        else:
            raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

        if not index_config.subscriptions:
            raise ConfigurationError(
                f'`{index_config.name}` index has no subscriptions; ensure that config is correct.'
            )

    def _resolve_index_links(self, index_config: ResolvedIndexConfigU) -> None:
        """Resolve contract and datasource configs by aliases.

        WARNING: str type checks are intentional! See `dipdup.config.patch_annotations`.
        """
        handler_config: HandlerConfig

        # NOTE: Each index must have a corresponding (currently) TzKT datasource
        if isinstance(index_config.datasource, str):
            if 'tzkt' in index_config.kind:
                index_config.datasource = self.get_tzkt_datasource(index_config.datasource)
            elif 'subsquid' in index_config.kind:
                index_config.datasource = self.get_subsquid_datasource(index_config.datasource)
            else:
                raise FrameworkException(f'Unknown datasource type for index `{index_config.name}`')

        if isinstance(index_config, TzktOperationsIndexConfig):
            if index_config.contracts is not None:
                for i, contract in enumerate(index_config.contracts):
                    if isinstance(contract, str):
                        index_config.contracts[i] = self.get_contract(contract)

            for handler_config in index_config.handlers:
                handler_config.parent = index_config
                for idx, pattern_config in enumerate(handler_config.pattern):
                    # NOTE: Untyped operations are named as `transaction_N` or `origination_N` based on their index
                    pattern_config._subgroup_index = idx

                    if isinstance(pattern_config, OperationsHandlerTransactionPatternConfig):
                        if isinstance(pattern_config.destination, str):
                            pattern_config.destination = self.get_contract(pattern_config.destination)
                        if isinstance(pattern_config.source, str):
                            pattern_config.source = self.get_contract(pattern_config.source)

                    elif isinstance(pattern_config, OperationsHandlerOriginationPatternConfig):
                        # TODO: Remove in 7.0
                        if pattern_config.similar_to:
                            raise FrameworkException('originated_contract` alias, should be replaced in __init__')

                        if isinstance(pattern_config.source, str):
                            pattern_config.source = self.get_contract(pattern_config.source)

                        if isinstance(pattern_config.originated_contract, str):
                            pattern_config.originated_contract = self.get_contract(pattern_config.originated_contract)

        elif isinstance(index_config, TzktBigMapsIndexConfig):
            for handler_config in index_config.handlers:
                handler_config.parent = index_config
                if isinstance(handler_config.contract, str):
                    handler_config.contract = self.get_contract(handler_config.contract)

        elif isinstance(index_config, TzktHeadIndexConfig):
            for handler_config in index_config.handlers:
                handler_config.parent = index_config

        elif isinstance(index_config, TzktTokenTransfersIndexConfig):
            for handler_config in index_config.handlers:
                handler_config.parent = index_config

                if isinstance(handler_config.contract, str):
                    handler_config.contract = self.get_contract(handler_config.contract)

        elif isinstance(index_config, TzktOperationsUnfilteredIndexConfig):
            index_config.handler_config.parent = index_config

        elif isinstance(index_config, TzktEventsIndexConfig):
            for handler_config in index_config.handlers:
                handler_config.parent = index_config

                if isinstance(handler_config.contract, str):
                    handler_config.contract = self.get_contract(handler_config.contract)

        elif isinstance(index_config, EvmSubsquidEventsIndexConfig):
            for handler_config in index_config.handlers:
                handler_config.parent = index_config

                if isinstance(handler_config.contract, str):
                    handler_config.contract = self.get_contract(handler_config.contract)

        elif isinstance(index_config, EvmSubsquidOperationsIndexConfig):
            ...

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
                config._name = name


# NOTE: Reimport to avoid circular imports
from dipdup.config.abi_etherscan import EtherscanDatasourceConfig
from dipdup.config.coinbase import CoinbaseDatasourceConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.config.evm_subsquid_events import EvmSubsquidEventsIndexConfig
from dipdup.config.evm_subsquid_operations import EvmSubsquidOperationsIndexConfig
from dipdup.config.http import HttpDatasourceConfig
from dipdup.config.ipfs import IpfsDatasourceConfig
from dipdup.config.tezos_tzkt import TzktDatasourceConfig
from dipdup.config.tezos_tzkt_big_maps import TzktBigMapsIndexConfig
from dipdup.config.tezos_tzkt_events import TzktEventsIndexConfig
from dipdup.config.tezos_tzkt_head import TzktHeadIndexConfig
from dipdup.config.tezos_tzkt_operations import OperationsHandlerOriginationPatternConfig
from dipdup.config.tezos_tzkt_operations import OperationsHandlerTransactionPatternConfig
from dipdup.config.tezos_tzkt_operations import TzktOperationsIndexConfig
from dipdup.config.tezos_tzkt_operations import TzktOperationsUnfilteredIndexConfig
from dipdup.config.tezos_tzkt_token_transfers import TzktTokenTransfersIndexConfig
from dipdup.config.tzip_metadata import TzipMetadataDatasourceConfig

# NOTE: Unions for Pydantic config deserialization
DatasourceConfigU = (
    TzktDatasourceConfig
    | CoinbaseDatasourceConfig
    | TzipMetadataDatasourceConfig
    | IpfsDatasourceConfig
    | HttpDatasourceConfig
    | SubsquidDatasourceConfig
    | EtherscanDatasourceConfig
)
ResolvedIndexConfigU = (
    EvmSubsquidEventsIndexConfig
    | EvmSubsquidOperationsIndexConfig
    | TzktOperationsIndexConfig
    | TzktBigMapsIndexConfig
    | TzktHeadIndexConfig
    | TzktTokenTransfersIndexConfig
    | TzktEventsIndexConfig
    | TzktOperationsUnfilteredIndexConfig
)
IndexConfigU = ResolvedIndexConfigU | IndexTemplateConfig


def patch_annotations(replace_table: dict[str, str]) -> None:
    """Patch dataclass annotations in runtime to allow using aliases in config files.

    DipDup YAML config uses string aliases for contracts and datasources. During `DipDupConfig.load` these
    aliases are resolved to actual configs from corresponding sections and never become strings again.
    This hack allows to add `str` in Unions before loading config so we don't need to write `isinstance(...)`
    checks everywhere.

    You can revert these changes by calling `patch_annotations(orinal_annotations)`, but tests will fail.
    """
    self = importlib.import_module(__name__)
    submodules = tuple(inspect.getmembers(self, inspect.ismodule))
    submodules += ((__name__, self),)

    for name, submodule in submodules:
        for attr in dir(submodule):
            value = getattr(submodule, attr)
            if hasattr(value, '__annotations__'):
                # NOTE: All annotations are strings now
                reload = False
                for name, annotation in value.__annotations__.items():
                    annotation = annotation if isinstance(annotation, str) else annotation.__class__.__name__
                    if new_annotation := replace_table.get(annotation):
                        value.__annotations__[name] = new_annotation
                        reload = True

                # NOTE: Wrap dataclass again to recreate magic methods
                if reload:
                    setattr(submodule, attr, dataclass(value))

            if hasattr(value, '__pydantic_model__'):
                value.__pydantic_model__.update_forward_refs()


yaml_annotations = {
    'TzktDatasourceConfig': 'str | TzktDatasourceConfig',
    'SubsquidDatasourceConfig': 'str | SubsquidDatasourceConfig',
    'ContractConfig': 'str | ContractConfig',
    'ContractConfig | None': 'str | ContractConfig | None',
    'list[ContractConfig]': 'list[str | ContractConfig]',
    'HookConfig': 'str | HookConfig',
}
orinal_annotations = {v: k for k, v in yaml_annotations.items()}
patch_annotations(yaml_annotations)
