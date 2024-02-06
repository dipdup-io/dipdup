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
import logging.config
import re
from abc import ABC
from abc import abstractmethod
from collections import Counter
from contextlib import suppress
from dataclasses import field
from pathlib import Path
from pydoc import locate
from typing import TYPE_CHECKING
from typing import Any
from typing import Generic
from typing import Literal
from typing import TypeVar
from typing import cast
from urllib.parse import quote_plus
from urllib.parse import urlparse

import orjson
from pydantic import validator
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder

from dipdup import env
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import FrameworkException
from dipdup.exceptions import IndexAlreadyExistsError
from dipdup.models import ReindexingAction
from dipdup.models import ReindexingReason
from dipdup.models import SkipHistory
from dipdup.utils import pascal_to_snake
from dipdup.yaml import DipDupYAMLConfig

if TYPE_CHECKING:
    from collections.abc import Iterator

    from dipdup.subscriptions import Subscription

DEFAULT_POSTGRES_SCHEMA = 'public'
DEFAULT_POSTGRES_DATABASE = 'postgres'
DEFAULT_POSTGRES_USER = 'postgres'
DEFAULT_POSTGRES_PORT = 5432
DEFAULT_SQLITE_PATH = ':memory:'


_logger = logging.getLogger(__name__)


@dataclass
class SqliteDatabaseConfig:
    """
    SQLite connection config

    :param kind: always 'sqlite'
    :param path: Path to .sqlite3 file, leave default for in-memory database (`:memory:`)
    :param immune_tables: List of tables to preserve during reindexing
    """

    kind: Literal['sqlite']
    path: str = DEFAULT_SQLITE_PATH
    immune_tables: set[str] = field(default_factory=set)

    @property
    def schema_name(self) -> str:
        # NOTE: Used only as identifier in `dipdup_schema` dable, since Hasura integration is not supported for SQLite.
        return DEFAULT_POSTGRES_SCHEMA

    @property
    def connection_string(self) -> str:
        return f'{self.kind}://{self.path}'

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
    :param request_timeout: Request timeout in seconds
    :param batch_size: Number of items fetched in a single paginated request
    :param replay_path: Use cached HTTP responses instead of making real requests (dev only)
    :param alias: Alias for this HTTP client (dev only)
    """

    retry_count: int | None = None
    retry_sleep: float | None = None
    retry_multiplier: float | None = None
    ratelimit_rate: int | None = None
    ratelimit_period: int | None = None
    ratelimit_sleep: float | None = None
    connection_limit: int | None = None
    connection_timeout: int | None = None
    request_timeout: int | None = None
    batch_size: int | None = None
    replay_path: str | None = None
    alias: str | None = None


@dataclass
class ResolvedHttpConfig:
    """HTTP client configuration with defaults"""

    retry_count: int = 10
    retry_sleep: float = 1.0
    retry_multiplier: float = 2.0
    ratelimit_rate: int = 0
    ratelimit_period: int = 0
    ratelimit_sleep: float = 0.0
    connection_limit: int = 100
    connection_timeout: int = 60
    request_timeout: int = 60
    batch_size: int = 10000
    replay_path: str | None = None
    alias: str | None = None

    @classmethod
    def create(
        cls,
        default: HttpConfig,
        user: HttpConfig | None,
    ) -> ResolvedHttpConfig:
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


class ContractConfig(ABC, NameMixin):
    """Contract config

    :param kind: Defined by child class
    :param typename: Alias for the contract script
    """

    kind: str
    typename: str | None

    @property
    def module_name(self) -> str:
        return self.typename or self.name

    @property
    def module_path(self) -> Path:
        return Path(*self.module_name.split('.'))


class DatasourceConfig(ABC, NameMixin):
    kind: str
    url: str
    http: HttpConfig | None


class AbiDatasourceConfig(DatasourceConfig): ...


class IndexDatasourceConfig(DatasourceConfig): ...


@dataclass
class CodegenMixin(ABC):
    """Base for pattern config classes containing methods required for codegen"""

    @abstractmethod
    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]: ...

    @abstractmethod
    def iter_arguments(self) -> Iterator[tuple[str, str]]: ...

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
class CallbackMixin(CodegenMixin):
    """Mixin for callback configs

    :param callback: Callback name
    """

    callback: str

    def __post_init_post_parse__(self) -> None:
        if self.callback and self.callback != pascal_to_snake(self.callback, strip_dots=False):
            raise ConfigurationError('`callback` field must be a valid Python module name')


@dataclass
class HandlerConfig(CallbackMixin, ParentMixin['IndexConfig']):
    def __post_init_post_parse__(self) -> None:
        CallbackMixin.__post_init_post_parse__(self)
        ParentMixin.__post_init_post_parse__(self)


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
class IndexConfig(ABC, NameMixin, ParentMixin['ResolvedIndexConfigU']):
    """Index config

    :param datasource: Alias of index datasource in `datasources` section
    """

    kind: str
    datasource: DatasourceConfig

    def __post_init_post_parse__(self) -> None:
        NameMixin.__post_init_post_parse__(self)
        ParentMixin.__post_init_post_parse__(self)

        self.template_values: dict[str, str] = {}

    @abstractmethod
    def get_subscriptions(self) -> set[Subscription]: ...

    def hash(self) -> str:
        """Calculate hash to ensure config has not changed since last run."""
        # FIXME: How to convert pydantic dataclass into dict without json.dumps? asdict is not recursive.
        config_json = orjson.dumps(self, default=pydantic_encoder)
        config_dict = orjson.loads(config_json)

        self.strip(config_dict)

        config_json = orjson.dumps(config_dict)
        return hashlib.sha256(config_json).hexdigest()

    @classmethod
    def strip(cls, config_dict: dict[str, Any]) -> None:
        """Strip config from tunables that are not needed for hash calculation."""
        config_dict['datasource'].pop('http', None)
        config_dict['datasource'].pop('buffer_size', None)


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
    :param camel_case: Whether to use camelCase instead of default pascal_case for the field names.
    :param rest: Enable REST API both for autogenerated and custom queries.
    :param http: HTTP connection tunables
    """

    url: str
    admin_secret: str | None = field(default=None, repr=False)
    create_source: bool = False
    source: str = 'default'
    select_limit: int = 1000
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
    :param args: Arguments to pass to the hook
    :param crontab: Schedule with crontab syntax (`* * * * *`)
    :param interval: Schedule with interval in seconds
    :param daemon: Run hook as a daemon (never stops)
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
        if not schedules_enabled:
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

    dsn: str
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
class HookConfig(CallbackMixin):
    """Hook config

    :param callback: Callback name
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
class SystemHookConfig(HookConfig):
    pass


system_hooks = {
    # NOTE: Fires on every run after datasources and schema are initialized.
    # NOTE: Default: nothing.
    'on_restart': SystemHookConfig(
        callback='on_restart',
    ),
    # NOTE: Fires on rollback which affects specific index and can't be processed unattended.
    # NOTE: Default: database rollback.
    'on_index_rollback': SystemHookConfig(
        callback='on_index_rollback',
        args={
            'index': 'dipdup.index.Index',
            'from_level': 'int',
            'to_level': 'int',
        },
    ),
    # NOTE: Fires when DipDup runs with empty schema, right after schema is initialized.
    # NOTE: Default: nothing.
    'on_reindex': SystemHookConfig(
        callback='on_reindex',
    ),
    # NOTE: Fires when all indexes reach REALTIME state.
    # NOTE: Default: nothing.
    'on_synchronized': SystemHookConfig(
        callback='on_synchronized',
    ),
}


@dataclass
class ApiConfig:
    host = '127.0.0.1'
    port: int = 46339  # dial INDEX 😎


@dataclass
class AdvancedConfig:
    """This section allows users to tune some system-wide options, either experimental or unsuitable for generic configurations.

    :param reindex: Mapping of reindexing reasons and actions DipDup performs
    :param scheduler: `apscheduler` scheduler config
    :param postpone_jobs: Do not start job scheduler until all indexes are in realtime state
    :param early_realtime: Spawn realtime datasources immediately after startup
    :param skip_version_check: Do not check for new DipDup versions on startup
    :param rollback_depth: A number of levels to keep for rollback
    :param decimal_precision: Overwrite precision if it's not guessed correctly based on project models.
    :param unsafe_sqlite: Disable journaling and data integrity checks. Use only for testing.
    :param alt_operation_matcher: Use different algorithm to match Tezos operations (dev only)
    """

    reindex: dict[ReindexingReason, ReindexingAction] = field(default_factory=dict)
    scheduler: dict[str, Any] | None = None
    postpone_jobs: bool = False
    early_realtime: bool = False
    skip_version_check: bool = False
    rollback_depth: int | None = None
    decimal_precision: int | None = None
    unsafe_sqlite: bool = False
    alt_operation_matcher: bool = False

    class Config:
        extra = 'allow'


@dataclass
class DipDupConfig:
    """Main indexer config

    :param spec_version: Version of config specification, currently always `2.0`
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
    :param api: Management API config
    :param advanced: Advanced config
    :param custom: User-defined configuration to use in callbacks
    :param logging: Modify logging verbosity
    """

    spec_version: str | float
    package: str
    datasources: dict[str, DatasourceConfigU] = field(default_factory=dict)
    database: SqliteDatabaseConfig | PostgresDatabaseConfig = field(
        default_factory=lambda *a, **kw: SqliteDatabaseConfig(kind='sqlite')
    )
    contracts: dict[str, ContractConfigU] = field(default_factory=dict)
    indexes: dict[str, IndexConfigU] = field(default_factory=dict)
    templates: dict[str, ResolvedIndexConfigU] = field(default_factory=dict)
    jobs: dict[str, JobConfig] = field(default_factory=dict)
    hooks: dict[str, HookConfig] = field(default_factory=dict)
    hasura: HasuraConfig | None = None
    sentry: SentryConfig | None = None
    prometheus: PrometheusConfig | None = None
    api: ApiConfig | None = None
    advanced: AdvancedConfig = field(default_factory=AdvancedConfig)
    custom: dict[str, Any] = field(default_factory=dict)
    logging: dict[str, str | int] | str | int = 'INFO'

    def __post_init_post_parse__(self) -> None:
        if self.package != pascal_to_snake(self.package):
            raise ConfigurationError('Python package name must be in snake_case.')

        self._paths: list[Path] = []
        self._environment: dict[str, str] = {}
        self._json = DipDupYAMLConfig()

    @property
    def schema_name(self) -> str:
        return self.database.schema_name

    @property
    def package_path(self) -> Path:
        return env.get_package_path(self.package)

    @property
    def abi_datasources(self) -> tuple[AbiDatasourceConfig, ...]:
        return tuple(c for c in self.datasources.values() if isinstance(c, AbiDatasourceConfig))

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

        config._paths = paths
        config._json = config_json
        config._environment = config_environment
        return config

    def get_contract(self, name: str) -> ContractConfig:
        try:
            return self.contracts[name]
        except KeyError as e:
            raise ConfigurationError(f'Contract `{name}` not found in `contracts` config section') from e

    def get_tezos_contract(self, name: str) -> TezosContractConfig:
        contract = self.get_contract(name)
        if not isinstance(contract, TezosContractConfig):
            raise ConfigurationError(f'Contract `{name}` is not a Tezos contract')
        return contract

    def get_evm_contract(self, name: str) -> EvmContractConfig:
        contract = self.get_contract(name)
        if not isinstance(contract, EvmContractConfig):
            raise ConfigurationError(f'Contract `{name}` is not an EVM contract')
        return contract

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

    def get_evm_node_datasource(self, name: str) -> EvmNodeDatasourceConfig:
        datasource = self.get_datasource(name)
        if not isinstance(datasource, EvmNodeDatasourceConfig):
            raise ConfigurationError('`datasource` field must refer to TzKT datasource')
        return datasource

    def set_up_logging(self) -> None:
        loglevels = {}
        if not isinstance(self.logging, dict):
            loglevels['dipdup'] = self.logging
            loglevels[self.package] = self.logging

        if env.DEBUG:
            loglevels['dipdup'] = 'DEBUG'
            loglevels[self.package] = 'DEBUG'

        for name, level in loglevels.items():
            try:
                if isinstance(level, str):
                    level = getattr(logging, level.upper())
                if not isinstance(level, int):
                    raise ValueError
            except (AttributeError, ValueError):
                raise ConfigurationError(f'Invalid logging level `{level}` for logger `{name}`') from None

            logging.getLogger(name).setLevel(level)

    def initialize(self) -> None:
        self._set_names()
        self._resolve_templates()
        self._resolve_links()
        self._validate()

    def dump(self) -> str:
        return DipDupYAMLConfig(
            **orjson.loads(
                orjson.dumps(
                    self,
                    default=pydantic_encoder,
                )
            )
        ).dump()

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
        index_config._name = name

    def _validate(self) -> None:
        # NOTE: Hasura and metadata interface
        if self.hasura:
            if isinstance(self.database, SqliteDatabaseConfig):
                raise ConfigurationError('SQLite database engine is not supported by Hasura')

        # NOTE: Hook names and callbacks
        for name, hook_config in self.hooks.items():
            if name != hook_config.callback:
                raise ConfigurationError(f'`{name}` hook name must be equal to `callback` value.')
            if name in system_hooks:
                raise ConfigurationError(f'`{name}` hook name is reserved by system hook')

        # NOTE: Rollback depth euristics and validation
        rollback_depth = self.advanced.rollback_depth
        if rollback_depth is None:
            rollback_depth = 0
            for name, datasource_config in self.datasources.items():
                if not isinstance(datasource_config, IndexDatasourceConfig):
                    continue
                rollback_depth = max(rollback_depth, datasource_config.rollback_depth or 0)

                if not isinstance(datasource_config, TzktDatasourceConfig):
                    continue
                if datasource_config.buffer_size and self.advanced.rollback_depth:
                    raise ConfigurationError(
                        f'`{name}`: `buffer_size` option is incompatible with `advanced.rollback_depth`'
                    )
        elif self.advanced.rollback_depth is not None and rollback_depth > self.advanced.rollback_depth:
            raise ConfigurationError(
                '`advanced.rollback_depth` cannot be less than the maximum rollback depth of all index datasources'
            )
        self.advanced.rollback_depth = rollback_depth

        if self.advanced.early_realtime:
            return

        # NOTE: Indexes that process only the current state imply early realtime.
        from dipdup.config.tezos_tzkt_big_maps import TzktBigMapsIndexConfig
        from dipdup.config.tezos_tzkt_token_balances import TzktTokenBalancesIndexConfig

        for name, index_config in self.indexes.items():
            is_big_maps = (
                isinstance(index_config, TzktBigMapsIndexConfig) and index_config.skip_history != SkipHistory.never
            )
            is_token_balances = isinstance(index_config, TzktTokenBalancesIndexConfig)
            if is_big_maps or is_token_balances:
                _logger.info('`%s` index is configured to skip history; implying `early_realtime` flag', name)
                self.advanced.early_realtime = True
                break

    def _resolve_template(self, template_config: IndexTemplateConfig) -> None:
        _logger.debug('Resolving index config `%s` from template `%s`', template_config.name, template_config.template)

        template = self.get_template(template_config.template)
        raw_template = orjson.dumps(template, default=pydantic_encoder).decode()
        for key, value in template_config.values.items():
            value_regex = r'<[ ]*' + key + r'[ ]*>'
            raw_template = re.sub(value_regex, value, raw_template)

        if missing_value := re.search(r'<*>', raw_template):
            raise ConfigurationError(
                f'`{template_config.name}` index config is missing required template value `{missing_value}`'
            )

        json_template = orjson.loads(raw_template)
        new_index_config = template.__class__(**json_template)
        new_index_config.template_values = template_config.values
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
        for datasource_config in self.datasources.values():
            if not isinstance(datasource_config, SubsquidDatasourceConfig):
                continue
            node_field = datasource_config.node
            if isinstance(node_field, str):
                datasource_config.node = self.datasources[node_field]
            elif isinstance(node_field, tuple):
                nodes = []
                for node in node_field:
                    nodes.append(self.get_evm_node_datasource(node) if isinstance(node, str) else node)
                datasource_config.node = tuple(nodes)

        for index_config in self.indexes.values():
            if isinstance(index_config, IndexTemplateConfig):
                raise ConfigInitializationException('Index templates must be resolved first')

            self._resolve_index_links(index_config)

        for job_config in self.jobs.values():
            if isinstance(job_config.hook, str):
                hook_config = self.get_hook(job_config.hook)
                if job_config.daemon and hook_config.atomic:
                    raise ConfigurationError('`HookConfig.atomic` and `JobConfig.daemon` flags are mutually exclusive')
                job_config.hook = hook_config

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
                        index_config.contracts[i] = self.get_tezos_contract(contract)

            for handler_config in index_config.handlers:
                handler_config.parent = index_config
                for idx, pattern_config in enumerate(handler_config.pattern):
                    # NOTE: Untyped operations are named as `transaction_N` or `origination_N` based on their index
                    pattern_config._subgroup_index = idx

                    if isinstance(pattern_config, OperationsHandlerTransactionPatternConfig):
                        if isinstance(pattern_config.destination, str):
                            pattern_config.destination = self.get_tezos_contract(pattern_config.destination)
                        if isinstance(pattern_config.source, str):
                            pattern_config.source = self.get_tezos_contract(pattern_config.source)

                    elif isinstance(pattern_config, OperationsHandlerOriginationPatternConfig):
                        if isinstance(pattern_config.source, str):
                            pattern_config.source = self.get_tezos_contract(pattern_config.source)

                        if isinstance(pattern_config.originated_contract, str):
                            pattern_config.originated_contract = self.get_tezos_contract(
                                pattern_config.originated_contract
                            )

                    elif isinstance(pattern_config, OperationsHandlerSmartRollupExecutePatternConfig):
                        if isinstance(pattern_config.destination, str):
                            pattern_config.destination = self.get_tezos_contract(pattern_config.destination)

        elif isinstance(index_config, TzktBigMapsIndexConfig):
            for handler_config in index_config.handlers:
                handler_config.parent = index_config
                if isinstance(handler_config.contract, str):
                    handler_config.contract = self.get_tezos_contract(handler_config.contract)

        elif isinstance(index_config, TzktHeadIndexConfig):
            index_config.handler_config.parent = index_config

        elif isinstance(index_config, TzktTokenTransfersIndexConfig):
            for handler_config in index_config.handlers:
                handler_config.parent = index_config

                if isinstance(handler_config.contract, str):
                    handler_config.contract = self.get_tezos_contract(handler_config.contract)

                if isinstance(handler_config.from_, str):
                    handler_config.from_ = self.get_tezos_contract(handler_config.from_)

                if isinstance(handler_config.to, str):
                    handler_config.to = self.get_tezos_contract(handler_config.to)

        elif isinstance(index_config, TzktTokenBalancesIndexConfig):
            for handler_config in index_config.handlers:
                handler_config.parent = index_config

                if isinstance(handler_config.contract, str):
                    handler_config.contract = self.get_tezos_contract(handler_config.contract)

        elif isinstance(index_config, TzktOperationsUnfilteredIndexConfig):
            index_config.handler_config.parent = index_config

        elif isinstance(index_config, TzktEventsIndexConfig):
            for handler_config in index_config.handlers:
                handler_config.parent = index_config

                if isinstance(handler_config.contract, str):
                    handler_config.contract = self.get_tezos_contract(handler_config.contract)

        elif isinstance(index_config, SubsquidEventsIndexConfig):
            for handler_config in index_config.handlers:
                handler_config.parent = index_config

                if isinstance(handler_config.contract, str):
                    handler_config.contract = self.get_evm_contract(handler_config.contract)

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


"""
WARNING: A very dark magic ahead. Be extra careful when editing code below.
"""

# NOTE: Reimport to avoid circular imports
from dipdup.config.abi_etherscan import EtherscanDatasourceConfig
from dipdup.config.coinbase import CoinbaseDatasourceConfig
from dipdup.config.evm import EvmContractConfig
from dipdup.config.evm_node import EvmNodeDatasourceConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.config.evm_subsquid_events import SubsquidEventsIndexConfig
from dipdup.config.http import HttpDatasourceConfig
from dipdup.config.ipfs import IpfsDatasourceConfig
from dipdup.config.tezos import TezosContractConfig
from dipdup.config.tezos_tzkt import TzktDatasourceConfig
from dipdup.config.tezos_tzkt_big_maps import TzktBigMapsIndexConfig
from dipdup.config.tezos_tzkt_events import TzktEventsIndexConfig
from dipdup.config.tezos_tzkt_head import TzktHeadIndexConfig
from dipdup.config.tezos_tzkt_operations import OperationsHandlerOriginationPatternConfig
from dipdup.config.tezos_tzkt_operations import OperationsHandlerSmartRollupExecutePatternConfig
from dipdup.config.tezos_tzkt_operations import OperationsHandlerTransactionPatternConfig
from dipdup.config.tezos_tzkt_operations import TzktOperationsIndexConfig
from dipdup.config.tezos_tzkt_operations import TzktOperationsUnfilteredIndexConfig
from dipdup.config.tezos_tzkt_token_balances import TzktTokenBalancesIndexConfig
from dipdup.config.tezos_tzkt_token_transfers import TzktTokenTransfersIndexConfig
from dipdup.config.tzip_metadata import TzipMetadataDatasourceConfig

# NOTE: Unions for Pydantic config deserialization
ContractConfigU = EvmContractConfig | TezosContractConfig
DatasourceConfigU = (
    CoinbaseDatasourceConfig
    | EtherscanDatasourceConfig
    | HttpDatasourceConfig
    | IpfsDatasourceConfig
    | SubsquidDatasourceConfig
    | EvmNodeDatasourceConfig
    | TzipMetadataDatasourceConfig
    | TzktDatasourceConfig
)
ResolvedIndexConfigU = (
    SubsquidEventsIndexConfig
    | TzktBigMapsIndexConfig
    | TzktEventsIndexConfig
    | TzktHeadIndexConfig
    | TzktOperationsIndexConfig
    | TzktOperationsUnfilteredIndexConfig
    | TzktTokenTransfersIndexConfig
    | TzktTokenBalancesIndexConfig
)
IndexConfigU = ResolvedIndexConfigU | IndexTemplateConfig


def _patch_annotations(replace_table: dict[str, str]) -> None:
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
        if not submodule.__name__.startswith('dipdup.config'):
            continue

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


_original_to_aliased = {
    'TzktDatasourceConfig': 'str | TzktDatasourceConfig',
    'SubsquidDatasourceConfig': 'str | SubsquidDatasourceConfig',
    'ContractConfig': 'str | ContractConfig',
    'ContractConfig | None': 'str | ContractConfig | None',
    'TezosContractConfig': 'str | TezosContractConfig',
    'TezosContractConfig | None': 'str | TezosContractConfig | None',
    'EvmContractConfig': 'str | EvmContractConfig',
    'EvmContractConfig | None': 'str | EvmContractConfig | None',
    'list[TezosContractConfig]': 'list[str | TezosContractConfig]',
    'HookConfig': 'str | HookConfig',
    'EvmNodeDatasourceConfig | tuple[EvmNodeDatasourceConfig, ...] | None': (
        'str | tuple[str, ...] | EvmNodeDatasourceConfig | tuple[EvmNodeDatasourceConfig, ...] | None'
    ),
}
_patch_annotations(_original_to_aliased)
