import hashlib
import importlib
import json
import logging.config
import os
import re
import sys
from collections import defaultdict
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
ENV_VARIABLE_REGEX = r'\${([\w]*):-(.*)}'

sys.path.append(os.getcwd())


def snake_to_camel(value: str) -> str:
    return ''.join(map(lambda x: x[0].upper() + x[1:], value.split('_')))


def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


@dataclass
class SqliteDatabaseConfig:
    """
    SQLite connection config

    :param path: Path to .sqlite3 file, leave default for in-memory database
    """

    kind: Literal['sqlite']
    path: str = ':memory:'

    @property
    def connection_string(self):
        return f'{self.kind}://{self.path}'


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

    kind: Union[Literal['postgres'], Literal['mysql']]
    host: str
    port: int
    user: str
    database: str
    password: str = ''

    @property
    def connection_string(self):
        return f'{self.kind}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}'


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


@dataclass
class TzktDatasourceConfig:
    """TzKT datasource config

    :param url: Base API url
    :param network: Corresponding network alias, only for sanity checks
    """

    kind: Literal['tzkt']
    url: str

    def __hash__(self):
        return hash(self.url)


@dataclass
class OperationHandlerPatternConfig:
    """Operation handler pattern config

    :param destination: Alias of the contract to match
    :param entrypoint: Contract entrypoint
    :
    """

    destination: Union[str, ContractConfig]
    entrypoint: str

    def __post_init_post_parse__(self):
        self._parameter_type_cls = None
        self._storage_type_cls = None

    @property
    def contract_config(self) -> ContractConfig:
        assert isinstance(self.destination, ContractConfig)
        return self.destination

    @property
    def parameter_type_cls(self) -> Type:
        if self._parameter_type_cls is None:
            raise Exception('Parameter type is not registered')
        return self._parameter_type_cls

    @parameter_type_cls.setter
    def parameter_type_cls(self, typ: Type) -> None:
        self._parameter_type_cls = typ

    @property
    def storage_type_cls(self) -> Type:
        if self._storage_type_cls is None:
            raise Exception('Storage type is not registered')
        return self._storage_type_cls

    @storage_type_cls.setter
    def storage_type_cls(self, typ: Type) -> None:
        self._storage_type_cls = typ


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
    datasource: Union[str, TzktDatasourceConfig]
    contract: Union[str, ContractConfig]
    handlers: List[OperationHandlerConfig]
    first_block: int = 0
    last_block: int = 0

    def __post_init_post_parse__(self):
        self._state: Optional[State] = None
        self._rollback_fn: Optional[Callable] = None
        self._template_values: Dict[str, str] = None

    def hash(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self,
                default=pydantic_encoder,
            ).encode(),
        ).hexdigest()

    @property
    def tzkt_config(self) -> TzktDatasourceConfig:
        assert isinstance(self.datasource, TzktDatasourceConfig)
        return self.datasource

    @property
    def contract_config(self) -> ContractConfig:
        assert isinstance(self.contract, ContractConfig)
        return self.contract

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

    @property
    def template_values(self) -> Optional[Dict[str, str]]:
        return self._template_values

    @template_values.setter
    def template_values(self, value: Dict[str, str]) -> None:
        self._template_values = value


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
    datasource: Union[str, TzktDatasourceConfig]
    contract: Union[str, ContractConfig]
    handlers: List[BigmapdiffHandlerConfig]

    @property
    def tzkt_config(self) -> TzktDatasourceConfig:
        assert isinstance(self.datasource, TzktDatasourceConfig)
        return self.datasource


@dataclass
class BlockHandlerConfig:
    callback: str
    pattern = None


@dataclass
class BlockIndexConfig:
    kind: Literal['block']
    datasource: Union[str, TzktDatasourceConfig]
    handlers: List[BlockHandlerConfig]

    @property
    def tzkt_config(self) -> TzktDatasourceConfig:
        assert isinstance(self.datasource, TzktDatasourceConfig)
        return self.datasource


@dataclass
class IndexTemplateConfig:
    template: str
    values: Dict[str, str]


IndexConfigT = Union[OperationIndexConfig, BigmapdiffIndexConfig, BlockIndexConfig, IndexTemplateConfig]
IndexConfigTemplateT = Union[OperationIndexConfig, BigmapdiffIndexConfig, BlockIndexConfig]


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
    indexes: Dict[str, IndexConfigT]
    templates: Optional[Dict[str, IndexConfigTemplateT]] = None
    database: Union[SqliteDatabaseConfig, DatabaseConfig] = SqliteDatabaseConfig(kind='sqlite')

    def __post_init_post_parse__(self):
        self._logger = logging.getLogger(__name__)
        for index_name, index_config in self.indexes.items():
            if isinstance(index_config, IndexTemplateConfig):
                template = self.templates[index_config.template]
                raw_template = json.dumps(template, default=pydantic_encoder)
                for key, value in index_config.values.items():
                    value_regex = r'<[ ]*' + key + r'[ ]*>'
                    raw_template = re.sub(value_regex, value, raw_template)
                json_template = json.loads(raw_template)
                self.indexes[index_name] = template.__class__(**json_template)
                self.indexes[index_name].template_values = index_config.values

        callback_patterns: Dict[str, List[List[OperationHandlerPatternConfig]]] = defaultdict(list)

        for index_config in self.indexes.values():
            if isinstance(index_config, OperationIndexConfig):
                if isinstance(index_config.datasource, str):
                    index_config.datasource = self.datasources[index_config.datasource]
                if isinstance(index_config.contract, str):
                    index_config.contract = self.contracts[index_config.contract]

                for handler in index_config.handlers:
                    if isinstance(handler.pattern, list):
                        callback_patterns[handler.callback].append(handler.pattern)
                        for pattern in handler.pattern:
                            if isinstance(pattern.destination, str):
                                pattern.destination = self.contracts[pattern.destination]
            else:
                raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

        for callback, patterns in callback_patterns.items():
            if len(patterns) > 1:

                def get_pattern_type(pattern: List[OperationHandlerPatternConfig]):
                    return '::'.join(map(lambda x: x.contract_config.module_name, pattern))

                pattern_types = list(map(get_pattern_type, patterns))
                if any(map(lambda x: x != pattern_types[0], pattern_types)):
                    raise ValueError(
                        f'Callback `{callback}` used multiple times with different signatures. '
                        f'Make sure you have specified contract typenames'
                    )

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
            raw_config = file.read()

        for match in re.finditer(ENV_VARIABLE_REGEX, raw_config):
            variable, default_value = match.group(1), match.group(2)
            value = env.get(variable)
            placeholder = '${' + variable + ':-' + default_value + '}'
            raw_config = raw_config.replace(placeholder, value or default_value)

        json_config = YAML(typ='base').load(raw_config)
        config = cls(**json_config)
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
                            f'{self.package}'
                            f'.types'
                            f'.{pattern.contract_config.module_name}'
                            f'.parameter'
                            f'.{camel_to_snake(pattern.entrypoint)}'
                        )
                        parameter_type_cls = getattr(parameter_type_module, snake_to_camel(pattern.entrypoint))
                        pattern.parameter_type_cls = parameter_type_cls

                        storage_type_module = importlib.import_module(
                            f'{self.package}' f'.types' f'.{pattern.contract_config.module_name}' f'.storage'
                        )
                        storage_type_cls = getattr(storage_type_module, 'Storage')
                        pattern.storage_type_cls = storage_type_cls


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
