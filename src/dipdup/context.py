import logging
import os
import sys
import time
from contextlib import contextmanager, suppress
from os.path import exists, join
from pprint import pformat
from typing import Any, Dict, Iterator, Optional, cast

import sqlparse  # type: ignore
from tortoise import Tortoise
from tortoise.transactions import get_connection

from dipdup.config import (
    ContractConfig,
    DipDupConfig,
    HandlerConfig,
    HookConfig,
    IndexConfig,
    IndexTemplateConfig,
    PostgresDatabaseConfig,
    default_hooks,
)
from dipdup.datasources.datasource import Datasource
from dipdup.exceptions import (
    CallbackError,
    CallbackNotImplementedError,
    CallbackTypeError,
    ConfigurationError,
    ContractAlreadyExistsError,
    IndexAlreadyExistsError,
    InitializationRequiredError,
)
from dipdup.utils import FormattedLogger, iter_files

ONETIME_ARGS = ('--reindex', '--hotswap')


# TODO: Dataclasses are cool, everyone loves them. Resolve issue with pydantic serialization.
class DipDupContext:
    def __init__(
        self,
        datasources: Dict[str, Datasource],
        config: DipDupConfig,
        callbacks: 'CallbackManager',
    ) -> None:
        self.datasources = datasources
        self.config = config
        self.callbacks = callbacks
        self.logger = FormattedLogger('dipdup.context')
        self._updated: bool = False

    def __str__(self) -> str:
        return pformat(self.__dict__)

    async def fire_hook(self, name: str, *args, **kwargs: Any) -> None:
        await self.callbacks.fire_hook(self, name, *args, **kwargs)

    async def fire_handler(self, name: str, datasource: Datasource, *args, **kwargs: Any) -> None:
        await self.callbacks.fire_handler(self, name, datasource, *args, **kwargs)

    async def execute_sql(self, name: str) -> None:
        await self.callbacks.execute_sql(self, name)

    def commit(self) -> None:
        """Spawn indexes after handler execution"""
        self._updated = True

    def reset(self) -> None:
        self._updated = False

    @property
    def updated(self) -> bool:
        return self._updated

    async def restart(self) -> None:
        """Restart preserving CLI arguments"""
        # NOTE: Remove --reindex from arguments to avoid reindexing loop
        if '--reindex' in sys.argv:
            sys.argv.remove('--reindex')
        os.execl(sys.executable, sys.executable, *sys.argv)

    async def reindex(self, reason: Optional[str] = None) -> None:
        """Drop all tables or whole database and restart with the same CLI arguments"""

        async def _recreate_schema(conn, name: str) -> None:
            await conn.execute_script(f'DROP SCHEMA IF EXISTS {name} CASCADE')
            await conn.execute_script(f'CREATE SCHEMA {name}')

        async def _move_table(conn, name: str, schema: str, new_schema: str) -> None:
            await conn.execute_script(f'ALTER TABLE {schema}.{name} SET SCHEMA {new_schema}')

        self.logger.warning('Reindexing initialized, reason: %s', reason)
        database_config = self.config.database
        if isinstance(database_config, PostgresDatabaseConfig):
            conn = get_connection(None)
            immune_schema_name = f'{database_config.schema_name}_immune'

            if database_config.immune_tables:
                await _recreate_schema(conn, immune_schema_name)

            for table in database_config.immune_tables:
                await _move_table(conn, table, database_config.schema_name, immune_schema_name)

            await _recreate_schema(conn, database_config.schema_name)

            for table in database_config.immune_tables:
                await _move_table(conn, table, immune_schema_name, database_config.schema_name)

        else:
            await Tortoise._drop_databases()
        await self.restart()

    def add_contract(self, name: str, address: str, typename: Optional[str] = None) -> None:
        if name in self.config.contracts:
            raise ContractAlreadyExistsError(self, name, address)
        contract_config = ContractConfig(
            address=address,
            typename=typename,
        )
        self.config.contracts[name] = contract_config
        self._updated = True

    def add_index(self, name: str, template: str, values: Dict[str, Any]) -> None:
        if name in self.config.indexes:
            raise IndexAlreadyExistsError(self, name)
        self.config.indexes[name] = IndexTemplateConfig(
            template=template,
            values=values,
        )
        self._updated = True


class HookContext(DipDupContext):
    """Hook callback context."""

    def __init__(
        self,
        datasources: Dict[str, Datasource],
        config: DipDupConfig,
        callbacks: 'CallbackManager',
        logger: FormattedLogger,
        hook_config: HookConfig,
    ) -> None:
        super().__init__(datasources, config, callbacks)
        self.logger = logger
        self.hook_config = hook_config


class TemplateValuesDict(dict):
    def __init__(self, ctx, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError as e:
            raise ConfigurationError(f'Index `{self.ctx.index_config.name}` requires `{key}` template value to be set') from e


class HandlerContext(DipDupContext):
    """Common handler context."""

    def __init__(
        self,
        datasources: Dict[str, Datasource],
        config: DipDupConfig,
        callbacks: 'CallbackManager',
        logger: FormattedLogger,
        handler_config: HandlerConfig,
        datasource: Datasource,
    ) -> None:
        super().__init__(datasources, config, callbacks)
        self.logger = logger
        self.handler_config = handler_config
        self.datasource = datasource
        template_values = cast(IndexConfig, handler_config.parent).template_values if handler_config.parent else {}
        self.template_values = TemplateValuesDict(self, **template_values)


class CallbackManager:
    def __init__(self, package: str) -> None:
        self._logger = logging.getLogger('dipdup.callback')
        self._package = package
        self._handlers: Dict[str, HandlerConfig] = {}
        self._hooks: Dict[str, HookConfig] = {}

    def register_handler(self, handler_config: HandlerConfig) -> None:
        if handler_config.callback not in self._handlers:
            self._handlers[handler_config.callback] = handler_config
            handler_config.initialize_callback_fn(self._package)

    def register_hook(self, hook_config: HookConfig) -> None:
        if hook_config.callback not in self._hooks:
            self._hooks[hook_config.callback] = hook_config
            hook_config.initialize_callback_fn(self._package)

    async def fire_handler(self, ctx: 'DipDupContext', name: str, datasource: Datasource, *args, **kwargs: Any) -> None:
        try:
            new_ctx = HandlerContext(
                datasources=ctx.datasources,
                config=ctx.config,
                callbacks=ctx.callbacks,
                logger=FormattedLogger(f'dipdup.handlers.{name}'),
                handler_config=self._handlers[name],
                datasource=datasource,
            )
        except KeyError as e:
            raise ConfigurationError(f'Attempt to fire unregistered handler `{name}`') from e

        with self._wrapper('handler', name):
            await new_ctx.handler_config.callback_fn(new_ctx, *args, **kwargs)

        if new_ctx.updated:
            ctx.commit()

    async def fire_hook(self, ctx: 'DipDupContext', name: str, *args, **kwargs: Any) -> None:
        try:
            ctx = HookContext(
                datasources=ctx.datasources,
                config=ctx.config,
                callbacks=ctx.callbacks,
                logger=FormattedLogger(f'dipdup.hooks.{name}'),
                hook_config=self._hooks[name],
            )
        except KeyError as e:
            raise ConfigurationError(f'Attempt to fire unregistered hook `{name}`') from e

        self._verify_arguments(ctx, *args, **kwargs)
        try:
            with self._wrapper('hook', name):
                await ctx.hook_config.callback_fn(ctx, *args, **kwargs)
        except CallbackNotImplementedError:
            if name == 'on_rollback':
                await ctx.reindex(f'reorg message received, `{name}` hook callback is not implemented.')
            if name not in default_hooks:
                self._logger.warning('`%s` hook callback is not implemented. Remove `raise` statement from it to hide this message.', name)

    async def execute_sql(self, ctx: 'DipDupContext', name: str) -> None:
        """Execute SQL included with project"""
        if not isinstance(ctx.config.database, PostgresDatabaseConfig):
            self._logger.warning('Skipping SQL hook `%s`: not supported on SQLite', name)
            return

        sql_path = join(ctx.config.package_path, 'sql')
        if not exists(sql_path):
            raise InitializationRequiredError

        paths = (
            # NOTE: `sql` directory -> relative/absolute path
            join(sql_path, name),
            name,
        )

        for path in paths:
            if exists(path):
                break
        else:
            # NOTE: Not exactly this type of error
            raise ConfigurationError(f'SQL file/directory `{name}` not exists')

        # NOTE: SQL hooks are executed on default connection
        connection = get_connection(None)

        for file in iter_files(sql_path, '.sql'):
            ctx.logger.info('Executing `%s`', file.name)
            sql = file.read()
            for statement in sqlparse.split(sql):
                # NOTE: Ignore empty statements
                with suppress(AttributeError):
                    await connection.execute_script(statement)

    @contextmanager
    def _wrapper(self, kind: str, name: str) -> Iterator[None]:
        try:
            start = time.perf_counter()
            yield
            diff = time.perf_counter() - start
            level = self._logger.info if diff > 1 else self._logger.debug
            level('`%s` %s callback executed in %s seconds', name, kind, diff)
        except CallbackNotImplementedError as e:
            raise CallbackNotImplementedError(kind, name) from e
        except Exception as e:
            raise CallbackError(kind, name) from e

    @classmethod
    def _verify_arguments(cls, ctx: HookContext, *args, **kwargs) -> None:
        kwargs_annotations = ctx.hook_config.locate_arguments()
        args_names = tuple(kwargs_annotations.keys())
        args_annotations = tuple(kwargs_annotations.values())

        for i, arg in enumerate(args):
            expected_type = args_annotations[i]
            if expected_type and not isinstance(arg, expected_type):
                raise CallbackTypeError(
                    name=ctx.hook_config.callback,
                    kind='hook',
                    arg=args_names[i],
                    type_=type(arg),
                    expected_type=expected_type,
                )
