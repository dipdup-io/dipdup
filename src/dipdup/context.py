import logging
import os
import sys
import time
from contextlib import suppress
from os.path import exists, join
from pprint import pformat
from typing import Any, Dict, Optional, cast

import sqlparse  # type: ignore
from tortoise import Tortoise
from tortoise.transactions import get_connection, in_transaction

from dipdup.config import ContractConfig, DipDupConfig, HandlerConfig, HookConfig, IndexConfig, IndexTemplateConfig, PostgresDatabaseConfig
from dipdup.datasources.datasource import Datasource
from dipdup.exceptions import (
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
        self.logger.warning('Reindexing initialized, reason: %s', reason)
        if isinstance(self.config.database, PostgresDatabaseConfig):
            exclude_expression = ''
            if self.config.database.immune_tables:
                immune_tables = [f"'{t}'" for t in self.config.database.immune_tables]
                exclude_expression = f' AND tablename NOT IN ({",".join(immune_tables)})'

            async with in_transaction() as conn:
                await conn.execute_script(
                    f'''
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema(){exclude_expression}) LOOP
                            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                        END LOOP;
                    END $$;
                    '''
                )
        else:
            await Tortoise._drop_databases()
        await self.restart()

    def add_contract(self, name: str, address: str, typename: Optional[str] = None) -> None:
        if name in self.config.contracts:
            raise ContractAlreadyExistsError(self, name, address)
        self.config.contracts[name] = ContractConfig(
            address=address,
            typename=typename,
        )
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

        start = time.perf_counter()
        await new_ctx.handler_config.callback_fn(new_ctx, *args, **kwargs)
        end = time.perf_counter()
        self._logger.debug(f'Handler `{name}` executed in {end - start:.3f}s')

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

        start = time.perf_counter()

        self._verify_arguments(ctx, *args, **kwargs)
        # NOTE: Not sure about order of hooks.
        await self._fire_sql_hook(ctx)
        await self._fire_python_hook(ctx, *args, **kwargs)

        end = time.perf_counter()
        self._logger.debug(f'Hook `{name}` executed in {end - start:.3f}s')

    async def _fire_python_hook(self, ctx: 'HookContext', *args, **kwargs) -> None:
        await ctx.hook_config.callback_fn(ctx, *args, **kwargs)

    async def _fire_sql_hook(self, ctx: 'HookContext') -> None:
        """Execute SQL included with project"""
        name = f'{ctx.hook_config.callback}.sql'
        sql_path = join(ctx.config.package_path, 'hooks', name)
        if not exists(sql_path):
            raise InitializationRequiredError

        if not isinstance(ctx.config.database, PostgresDatabaseConfig):
            self._logger.warning('Skipping SQL hook `%s`: not supported on SQLite', name)
            return

        # NOTE: SQL hooks are executed on default connection
        connection = get_connection(None)

        for file in iter_files(sql_path, '.sql'):
            ctx.logger.info('Executing `%s`', file.name)
            sql = file.read()
            for statement in sqlparse.split(sql):
                # NOTE: Ignore empty statements
                with suppress(AttributeError):
                    await connection.execute_script(statement)

    @classmethod
    def _verify_arguments(cls, ctx: HookContext, *args, **kwargs) -> None:
        kwargs_annotations = ctx.hook_config.locate_arguments()
        args_names = tuple(kwargs_annotations.keys())
        args_annotations = tuple(kwargs_annotations.values())

        for i, arg in enumerate(args):
            expected_type = args_annotations[i]
            if expected_type and not isinstance(arg, expected_type):
                raise CallbackTypeError(
                    ctx=ctx,
                    callback=ctx.hook_config.callback,
                    arg=args_names[i],
                    type_=type(arg),
                    expected_type=expected_type,
                )
