import textwrap
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Dict
from typing import Optional
from typing import Type

from tabulate import tabulate
from tortoise.models import Model

from dipdup import spec_version_mapping
from dipdup.enums import ReindexingReason

_tab = ('_' * 80) + '\n\n'


def unindent(text: str) -> str:
    """Remove indentation from text"""
    return textwrap.dedent(text).strip()


def indent(text: str, indent: int = 2) -> str:
    """Add indentation to text"""
    return textwrap.indent(text, ' ' * indent)


class DipDupException(Exception):
    message: str

    def __init__(self, *args: Any) -> None:
        super().__init__(self.message, *args)


class ConfigInitializationException(DipDupException):
    message = 'Config is not initialized. Some stage was skipped. Call `pre_initialize` or `initialize`.'


@dataclass(repr=False)
class DipDupError(Exception):
    """Unknown DipDup error"""

    def __str__(self) -> str:
        if not self.__doc__:
            raise NotImplementedError(f'{self.__class__.__name__} has no docstring')
        return self.__doc__

    def _help(self) -> str:
        return """
            An unexpected error has occurred!

            Please file a bug report at https://github.com/dipdup-net/dipdup/issues
        """

    def help(self) -> str:
        return unindent(self._help())

    def format(self) -> str:
        return _tab + self.help() + '\n'


@dataclass(repr=False)
class DatasourceError(DipDupError):
    """One of datasources returned an error"""

    msg: str
    datasource: str

    def _help(self) -> str:
        return f"""
            `{self.datasource}` datasource returned an error: {self.msg}

            Please file a bug report at https://github.com/dipdup-net/dipdup/issues
        """


@dataclass(repr=False)
class ConfigurationError(DipDupError):
    """DipDup YAML config is invalid"""

    msg: str

    def _help(self) -> str:
        return f"""
            {self.msg}

            DipDup config reference: https://docs.dipdup.net/config
        """


@dataclass(repr=False)
class DatabaseConfigurationError(ConfigurationError):
    """DipDup can't initialize database with given models and parameters"""

    model: Type[Model]

    def _help(self) -> str:
        return f"""
            {self.msg}

            Model: `{self.model._meta._model.__name__}`
            Table: `{self.model._meta.db_table}`

            Tortoise ORM examples: https://tortoise-orm.readthedocs.io/en/latest/examples.html
            DipDup config reference: https://docs.dipdup.net/config/database
        """


@dataclass(repr=False)
class MigrationRequiredError(DipDupError):
    """Project and DipDup spec versions don't match"""

    from_: str
    to: str
    reindex: bool = False

    def _help(self) -> str:
        version_table = tabulate(
            [
                ['current', self.from_, spec_version_mapping[self.from_]],
                ['required', self.to, spec_version_mapping[self.to]],
            ],
            headers=['', 'spec_version', 'DipDup version'],
        )
        reindex = '\n\n' + _tab + ReindexingRequiredError(ReindexingReason.migration).help() if self.reindex else ''
        return f"""
            Project migration required!

            {version_table.strip()}

            Perform the following actions:

              1. Run `dipdup migrate`.
              2. Review and commit changes.

            See https://docs.dipdup.net/release-notes for more information. {reindex}
        """


@dataclass(repr=False)
class ReindexingRequiredError(DipDupError):
    """Unable to continue indexing with existing database"""

    reason: ReindexingReason
    context: Dict[str, Any] = field(default_factory=dict)

    def _help(self) -> str:
        # FIXME: Indentation hell
        prefix = '\n' + ' ' * 14
        context = prefix.join(f'{k}: {v}' for k, v in self.context.items())
        if context:
            context = '{prefix}{context}\n'.format(prefix=prefix, context=context)

        return """
            Reindexing required! Reason: {reason}.
              {context}
            You may want to backup database before proceeding. After that perform one of the following actions:

              * Eliminate the cause of reindexing and run `dipdup schema approve`.
              * Drop database and start indexing from scratch with `dipdup schema wipe` command.

            See https://docs.dipdup.net/advanced/reindexing for more information.
        """.format(
            reason=self.reason.value,
            context=context,
        )


@dataclass(repr=False)
class InitializationRequiredError(DipDupError):
    """Project initialization required"""

    message: str

    def _help(self) -> str:
        return f"""
            Project initialization required! Reason: {self.message}.

            Perform the following actions:

              * Run `dipdup init`.
              * Review and commit changes.
        """


@dataclass(repr=False)
class ProjectImportError(DipDupError):
    """Can't import type or callback from the project package"""

    module: str
    obj: Optional[str] = None

    def _help(self) -> str:
        what = f'`{self.obj}` from' if self.obj else ''
        return f"""
            Failed to import {what} module `{self.module}`.

            Reasons in order of possibility:

              1. `init` command has not been called after modifying the config
              2. Type or callback has been renamed or removed manually
              3. `package` name is occupied by existing non-DipDup package
              4. Package exists, but not discoverable - check `$PYTHONPATH`
        """


@dataclass(repr=False)
class ContractAlreadyExistsError(DipDupError):
    """Attempt to add a contract with alias or address already in use"""

    ctx: Any
    name: str
    address: str

    def _help(self) -> str:
        contracts_table = indent(
            tabulate(
                [(c.name, c.address) for c in self.ctx.config.contracts.values()],
                tablefmt='plain',
            )
        )
        return f"""
            Contract with name `{self.name}` or address `{self.address}` already exists.

            Active contracts:

            {contracts_table}
        """


@dataclass(repr=False)
class IndexAlreadyExistsError(DipDupError):
    """Attemp to add an index with an alias already in use"""

    ctx: Any
    name: str

    def _help(self) -> str:
        indexes_table = indent(
            tabulate(
                [(c.name, c.kind) for c in self.ctx.config.indexes.values()],
                tablefmt='plain',
            )
        )
        return f"""
            Index with name `{self.name}` already exists.

            Active indexes:

            {indexes_table}
        """


@dataclass(repr=False)
class InvalidDataError(DipDupError):
    """Failed to validate datasource message against generated type class"""

    type_cls: Type[Any]
    data: Any
    parsed_object: Any

    def _help(self) -> str:

        return f"""
            Failed to validate datasource message against generated type class.

            Expected type:
            `{self.type_cls.__name__}`

            Invalid data:
            {self.data}

            Parsed object:
            {self.parsed_object}
        """


@dataclass(repr=False)
class CallbackError(DipDupError):
    """An error occured during callback execution"""

    module: str
    exc: Exception

    def _help(self) -> str:
        return f"""
            `{self.module}` callback execution failed:

              {self.exc.__class__.__name__}: {self.exc}
            
            Eliminate the reason of failure and restart DipDup.
        """


@dataclass(repr=False)
class CallbackTypeError(DipDupError):
    """Agrument of invalid type was passed to a callback"""

    kind: str
    name: str

    arg: str
    type_: Type[Any]
    expected_type: Type[Any]

    def _help(self) -> str:
        return f"""
            `{self.name}` {self.kind} callback was called with an argument of invalid type.

              argument: `{self.arg}`
              type: {self.type_}
              expected type: {self.expected_type}

            Make sure to set correct typenames in config and run `dipdup init --overwrite-types` to regenerate typeclasses.
        """


@dataclass(repr=False)
class HasuraError(DipDupError):
    """Failed to configure Hasura instance"""

    msg: str

    def _help(self) -> str:
        return f"""
            Failed to configure Hasura:

              {self.msg}

            Check out Hasura logs for more information.

            GraphQL integration docs: https://docs.dipdup.net/graphql/
        """


@dataclass(repr=False)
class ConflictingHooksError(DipDupError):
    """Project contains hooks that conflict with each other"""

    old: str
    new: str

    def _help(self) -> str:
        return f"""
            `{self.old}` hook was superseded by the `{self.new}` one; they can't be used together.

            Perform one of the following actions:

              * Follow the docs to migrate to the `{self.new}` hook, then remove `{self.old}` hook from the project.
              * Remove `{self.new}` hook from the project to preserve current behavior.

            Release notes: https://docs.dipdup.net/release-notes/
        """
