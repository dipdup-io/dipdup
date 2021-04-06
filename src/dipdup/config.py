import hashlib
import importlib
import json
import logging.config
import os
import sys
from os import environ as env
from os.path import dirname
from typing import Any, Callable, Dict, List, Optional, Type, Union

from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder
from ruamel.yaml import YAML
from tortoise import Tortoise
from typing_extensions import Literal

from dipdup.models import IndexType, State

ROLLBACK_HANDLER = 'on_rollback'


@dataclass
class SqliteDatabaseConfig:
    """
    SQLite connection config

    :param path: Path to .sqlite3 file, leave default for in-memory database
    """

    path: str = ':memory:'

    @property
    def connection_string(self):
        return f'sqlite://{self.path}'


@dataclass
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
    database: str
    password: str = ''

    def __post_init_post_parse__(self):
        if not self.password:
            self.password = env.get('DIPDUP_DATABASE_PASSWORD', '')

    @property
    def connection_string(self):
        return f'{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}'


@dataclass
class TzktDatasourceConfig:
    """TzKT datasource config

    :param url: Base API url
    :param network: Corresponding network alias, only for sanity checks
    """

    kind: Literal['tzkt']
    url: str
    network: Optional[str] = None


@dataclass
class OperationHandlerPatternConfig:
    """Operation handler pattern config

    :param destination: Alias of the contract to match
    :param entrypoint: Contract entrypoint
    :
    """

    destination: str
    entrypoint: str

    def __post_init_post_parse__(self):
        self._parameter_type_cls = None

    @property
    def parameter_type_cls(self) -> Type:
        if self._parameter_type_cls is None:
            raise Exception('Parameter type is not registered')
        return self._parameter_type_cls

    @parameter_type_cls.setter
    def parameter_type_cls(self, typ: Type) -> None:
        self._parameter_type_cls = typ


@dataclass
class OperationHandlerConfig:
    """Operation handler config

    :param callback: Name of method in `handlers` package
    :param pattern: Filters to match operations in group
    """

    callback: str
    pattern: List[OperationHandlerPatternConfig]

    def __post_init_post_parse__(self):
        self._callback_fn = None

    @property
    def callback_fn(self) -> Callable:
        if self._callback_fn is None:
            raise Exception('Handler callable is not registered')
        return self._callback_fn

    @callback_fn.setter
    def callback_fn(self, fn: Callable) -> None:
        self._callback_fn = fn


@dataclass
class OperationIndexConfig:
    """Operation index config

    :param datasource: Alias of datasource in `datasources` block
    :param contract: Alias of contract to fetch operations for
    :param first_block: First block to process
    :param last_block: Last block to process
    :param handlers: List of indexer handlers
    """

    kind: Literal["operation"]
    datasource: str
    contract: str
    handlers: List[OperationHandlerConfig]
    first_block: int = 0
    last_block: int = 0

    def __post_init_post_parse__(self):
        self._state: Optional[State] = None
        self._rollback_fn: Optional[Callable] = None

    def hash(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self,
                default=pydantic_encoder,
            ).encode(),
        ).hexdigest()

    @property
    def state(self):
        if not self._state:
            raise Exception('Config is not initialized')
        return self._state

    @state.setter
    def state(self, value: State):
        self._state = value

    @property
    def rollback_fn(self) -> Callable:
        if not self._rollback_fn:
            raise Exception('Config is not initialized')
        return self._rollback_fn

    @rollback_fn.setter
    def rollback_fn(self, value: Callable) -> None:
        self._rollback_fn = value


@dataclass
class BigmapdiffHandlerPatternConfig:
    name: str
    entry_type: str


@dataclass
class BigmapdiffHandlerConfig:
    callback: str
    pattern: List[BigmapdiffHandlerPatternConfig]


@dataclass
class BigmapdiffIndexConfig:
    kind: Literal['bigmapdiff']
    datasource: str
    contract: str
    handlers: List[BigmapdiffHandlerConfig]


@dataclass
class BlockHandlerConfig:
    callback: str
    pattern = None


@dataclass
class BlockIndexConfig:
    kind: Literal['block']
    datasource: str
    handlers: List[BlockHandlerConfig]


@dataclass
class ContractConfig:
    """Contract config

    :param network: Corresponding network alias, only for sanity checks
    :param address: Contract address
    """

    address: str
    network: Optional[str] = None


@dataclass
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
    contracts: Dict[str, ContractConfig]
    datasources: Dict[str, Union[TzktDatasourceConfig]]
    indexes: Dict[str, Union[OperationIndexConfig, BigmapdiffIndexConfig, BlockIndexConfig]]
    database: Union[SqliteDatabaseConfig, DatabaseConfig] = SqliteDatabaseConfig()

    def __post_init_post_parse__(self):
        self._logger = logging.getLogger(__name__)
        for index_config in self.indexes.values():
            if isinstance(index_config, OperationIndexConfig):
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
    ) -> 'DipDupConfig':

        current_workdir = os.path.join(os.getcwd())
        filename = os.path.join(current_workdir, filename)

        with open(filename) as file:
            raw_config = YAML(typ='base').load(file.read())
        config = cls(**raw_config)
        return config

    async def initialize(self) -> None:
        self._logger.info('Setting up handlers and types for package `%s`', self.package)

        rollback_fn = getattr(importlib.import_module(f'{self.package}.handlers.{ROLLBACK_HANDLER}'), ROLLBACK_HANDLER)

        for index_name, index_config in self.indexes.items():
            if isinstance(index_config, OperationIndexConfig):
                self._logger.info('Getting state for index `%s`', index_name)
                index_config.rollback_fn = rollback_fn
                index_hash = index_config.hash()
                state = await State.get_or_none(
                    index_name=index_name,
                    index_type=IndexType.operation,
                )
                if state is None:
                    state = State(
                        index_name=index_name,
                        index_type=IndexType.operation,
                        hash=index_hash,
                    )
                    await state.save()

                elif state.hash != index_hash:
                    self._logger.warning('Config hash mismatch, reindexing')
                    await Tortoise._drop_databases()
                    os.execl(sys.executable, sys.executable, *sys.argv)

                index_config.state = state

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
