import importlib
import logging.config
import os
from os.path import dirname
from typing import Any, Callable, Dict, List, Optional, Type, Union

from attr import dataclass
from cattrs_extras.converter import Converter
from ruamel.yaml import YAML


@dataclass(kw_only=True)
class SqliteDatabaseConfig:
    """
    SQLite connection config

    :param path: Path to .sqlite3 file, leave default for in-memory database
    """

    path: str = ':memory:'

    @property
    def connection_string(self):
        return f'sqlite://{self.path}'


@dataclass(kw_only=True)
class DatabaseConfig:
    """Database connection config

    :param driver: One of postgres/mysql (asyncpg and aiomysql libs must be installed respectively)
    :param host: Host
    :param port: Port
    :param user: User
    :param password: Password
    :param database: Schema name
    """

    driver: str
    host: str
    port: int
    user: str
    password: str = ''
    database: str

    @property
    def connection_string(self):
        return f'{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}'


@dataclass(kw_only=True)
class TzktDatasourceConfig:
    """TzKT datasource config

    :param url: Base API url
    :param network: Corresponding network alias, only for sanity checks
    """

    url: str
    network: Optional[str] = None


@dataclass(kw_only=True)
class OperationHandlerPatternConfig:
    """Operation handler pattern config

    :param destination: Alias of the contract to match
    :param entrypoint: Contract entrypoint
    :
    """

    destination: str
    entrypoint: str

    def __attrs_post_init__(self):
        self._parameter_type_cls = None

    @property
    def parameter_type_cls(self) -> Type:
        if self._parameter_type_cls is None:
            raise Exception('Parameter type is not registered')
        return self._parameter_type_cls

    @parameter_type_cls.setter
    def parameter_type_cls(self, typ: Type) -> None:
        self._parameter_type_cls = typ


@dataclass(kw_only=True)
class OperationHandlerConfig:
    """Operation handler config

    :param callback: Name of method in `hanflers` package
    :param pattern: Filters to match operations in group
    """

    callback: str
    pattern: List[OperationHandlerPatternConfig]

    def __attrs_post_init__(self):
        self._callback_fn = None

    @property
    def callback_fn(self) -> Callable:
        if self._callback_fn is None:
            raise Exception('Handler callable is not registered')
        return self._callback_fn

    @callback_fn.setter
    def callback_fn(self, fn: Callable) -> None:
        self._callback_fn = fn


@dataclass(kw_only=True)
class OperationIndexConfig:
    """Operation index config

    :param datasource: Alias of datasource in `datasources` block
    :param contract: Alias of contract to fetch operations for
    :param first_block: First block to process
    :param last_block: Last block to process
    :param handlers: List of indexer handlers
    """

    datasource: str
    contract: str
    first_block: int = 0
    last_block: int = 0
    handlers: List[OperationHandlerConfig]


@dataclass(kw_only=True)
class BigmapdiffHandlerPatternConfig:
    name: str
    entry_type: str


@dataclass(kw_only=True)
class BigmapdiffHandlerConfig:
    callback: str
    pattern: List[BigmapdiffHandlerPatternConfig]


@dataclass(kw_only=True)
class BigmapdiffIndexConfig:
    datasource: str
    contract: str
    handlers: List[BigmapdiffHandlerConfig]


@dataclass(kw_only=True)
class BlockHandlerConfig:
    callback: str
    pattern: None = None


@dataclass(kw_only=True)
class BlockIndexConfig:
    datasource: str
    handlers: List[BlockHandlerConfig]


@dataclass(kw_only=True)
class ContractConfig:
    """Contract config

    :param network: Corresponding network alias, only for sanity checks
    :param address: Contract address
    """

    network: Optional[str] = None
    address: str


@dataclass(kw_only=True)
class DatasourcesConfig:
    tzkt: TzktDatasourceConfig


@dataclass(kw_only=True)
class IndexesConfig:
    operation: Optional[OperationIndexConfig] = None
    bigmapdiff: Optional[BigmapdiffIndexConfig] = None
    block: Optional[BlockIndexConfig] = None


@dataclass(kw_only=True)
class DipDupConfig:
    """Main dapp config

    :param spec_version: Version of specification, always 0.0.1 for now
    :param package: Name of dapp python package, existing or not
    :param database: Database config
    :param contracts: Mapping of contract aliases and contract configs
    :param datasources: Mapping of datasource aliases and datasource configs
    :param indexes: Mapping of index aliases and index configs
    """

    spec_version: str
    package: str
    database: Union[SqliteDatabaseConfig, DatabaseConfig] = SqliteDatabaseConfig()
    contracts: Dict[str, ContractConfig]
    datasources: Dict[str, DatasourcesConfig]
    indexes: Dict[str, IndexesConfig]

    def __attrs_post_init__(self):
        self._logger = logging.getLogger(__name__)
        for indexes_config in self.indexes.values():
            if indexes_config.operation:
                index_config = indexes_config.operation
                if index_config is None:
                    continue
                index_config.contract = self.contracts[index_config.contract].address
                for handler in index_config.handlers:
                    for pattern in handler.pattern:
                        pattern.destination = self.contracts[pattern.destination].address

    @property
    def package_path(self) -> str:
        package = importlib.import_module(self.package)
        return dirname(package.__file__)

    @classmethod
    def load(
        cls,
        filename: str,
        cls_override: Optional[Type] = None,
        converter_override: Optional[Converter] = None,
    ) -> 'DipDupConfig':

        current_workdir = os.path.join(os.getcwd())
        filename = os.path.join(current_workdir, filename)
        converter = converter_override or Converter()

        with open(filename) as file:
            raw_config = YAML(typ='base').load(file.read())
        config = converter.structure(raw_config, cls_override or cls)
        return config

    def initialize(self) -> None:
        self._logger.info('Setting up handlers and types for package `%s`', self.package)

        for indexes_config in self.indexes.values():
            if indexes_config.operation:
                index_config = indexes_config.operation
                if not index_config:
                    continue
                for handler in index_config.handlers:
                    self._logger.info('Registering handler callback `%s`', handler.callback)
                    handler_module = importlib.import_module(f'{self.package}.handlers.{handler.callback}')
                    callback_fn = getattr(handler_module, handler.callback)
                    handler.callback_fn = callback_fn

                    for pattern in handler.pattern:
                        self._logger.info('Registering parameter type for entrypoint `%s`', pattern.entrypoint)
                        parameter_type_module = importlib.import_module(
                            f'{self.package}.types.{pattern.destination}.parameter.{pattern.entrypoint}'
                        )
                        parameter_type = pattern.entrypoint.title().replace('_', '')
                        parameter_type_cls = getattr(parameter_type_module, parameter_type)
                        pattern.parameter_type_cls = parameter_type_cls


@dataclass(kw_only=True)
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
