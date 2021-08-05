import os
import sys
from pprint import pformat
from typing import Any, Dict, Optional

from tortoise import Tortoise
from tortoise.transactions import in_transaction

from dipdup.config import ContractConfig, DipDupConfig, IndexConfig, IndexTemplateConfig, PostgresDatabaseConfig
from dipdup.datasources.datasource import Datasource
from dipdup.exceptions import ConfigurationError, ContractAlreadyExistsError, IndexAlreadyExistsError
from dipdup.utils import FormattedLogger


# TODO: Dataclasses are cool, everyone loves them. Resolve issue with pydantic serialization.
class DipDupContext:
    def __init__(
        self,
        datasources: Dict[str, Datasource],
        config: DipDupConfig,
    ) -> None:
        self.datasources = datasources
        self.config = config
        self._updated: bool = False

    def __str__(self) -> str:
        return pformat(self.__dict__)

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

    async def reindex(self) -> None:
        """Drop all tables or whole database and restart with the same CLI arguments"""
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
        logger: FormattedLogger,
        template_values: Dict[str, str],
        datasource: Datasource,
        index_config: IndexConfig,
    ) -> None:
        super().__init__(datasources, config)
        self.logger = logger
        self.template_values = TemplateValuesDict(self, **template_values)
        self.datasource = datasource
        self.index_config = index_config

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
        self.config.get_template(template)
        self.config.indexes[name] = IndexTemplateConfig(
            template=template,
            values=values,
        )
        # NOTE: Notify datasource to subscribe to operations by entrypoint if enabled in index config
        self.config.indexes[name].parent = self.index_config
        self._updated = True


class JobContext(DipDupContext):
    """Job handler context."""

    def __init__(
        self,
        datasources: Dict[str, Datasource],
        config: DipDupConfig,
        logger: FormattedLogger,
    ) -> None:
        super().__init__(datasources, config)
        self.logger = logger

    # TODO: Spawning indexes from jobs?


class RollbackHandlerContext(DipDupContext):
    def __init__(
        self,
        datasources: Dict[str, Datasource],
        config: DipDupConfig,
        logger: FormattedLogger,
        datasource: Datasource,
        from_level: int,
        to_level: int,
    ) -> None:
        super().__init__(datasources, config)
        self.logger = logger
        self.datasource = datasource
        self.from_level = from_level
        self.to_level = to_level
