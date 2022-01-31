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

    def __init__(self, *args) -> None:
        super().__init__(self.message, *args)


class ConfigInitializationException(DipDupException):
    message = 'Config is not initialized. Some stage was skipped. Call `pre_initialize` or `initialize`.'


@dataclass(frozen=True, repr=False)
class DipDupError(Exception):
    """Unknown DipDup error"""

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}: {self.__doc__}'

    def _help(self) -> str:
        # TODO: Update guide
        return """
            Unexpected error occurred!

            Please file a bug report at https://github.com/dipdup-net/dipdup/issues and attach the following:

              * `dipdup.yml` config. Make sure to remove sensitive information.
              * Reasonable amount of logs before the crash.
        """

    def help(self) -> str:
        return unindent(self._help())

    def format(self) -> str:
        return _tab + self.help() + '\n'


@dataclass(frozen=True, repr=False)
class DatasourceError(DipDupError):
    """One of datasources returned an error"""

    msg: str
    datasource: str

    def _help(self) -> str:
        return f"""
            `{self.datasource}` datasource returned an error: {self.msg}

            Most likely, this is a DipDup bug. Please file a bug report at https://github.com/dipdup-net/dipdup/issues
        """


@dataclass(frozen=True, repr=False)
class ConfigurationError(DipDupError):
    """DipDup YAML config is invalid"""

    msg: str

    def _help(self) -> str:
        return f"""
            {self.msg}

            DipDup config reference: https://docs.dipdup.net/config-file-reference
        """


@dataclass(frozen=True, repr=False)
class DatabaseConfigurationError(ConfigurationError):
    """DipDup can't initialize database with given models and parameters"""

    model: Type[Model]

    def _help(self) -> str:
        return f"""
            {self.msg}

            Model: `{self.model.__class__.__name__}`
            Table: `{self.model._meta.db_table}`

            Tortoise ORM examples: https://tortoise-orm.readthedocs.io/en/latest/examples.html
            DipDup config reference: https://docs.dipdup.net/config-file-reference/database
        """


@dataclass(frozen=True, repr=False)
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
        reindex = '\n\n' + _tab + ReindexingRequiredError(ReindexingReason.MIGRATION).help() if self.reindex else ''
        return f"""
            Project migration required!

            {version_table.strip()}

              1. Run `dipdup migrate`
              2. Review and commit changes

            See https://baking-bad.org/blog/ for additional release information. {reindex}
        """


@dataclass(frozen=True, repr=False)
class ReindexingRequiredError(DipDupError):
    """Unable to continue indexing with existing database"""

    reason: ReindexingReason
    context: Dict[str, Any] = field(default_factory=dict)

    def _help(self) -> str:
        additional_context = '\n              '.join(f'{k}: {v}' for k, v in self.context.items())
        return f"""
            Reindexing required!

            Reason: {self.reason.value}

            Additional context:

                {additional_context}

            You may want to backup database before proceeding. After that perform one of the following actions:

                * Eliminate the cause of reindexing and run `dipdup schema approve`.
                * Drop database and start indexing from scratch with `dipdup schema wipe` command.
        """


@dataclass(frozen=True, repr=False)
class InitializationRequiredError(DipDupError):
    message: str

    def _help(self) -> str:
        return f"""
            Project initialization required!

            Reason: {self.message}

            1. Run `dipdup init`
            2. Review and commit changes
        """


@dataclass(frozen=True, repr=False)
class HandlerImportError(DipDupError):
    """Can't perform import from handler module"""

    module: str
    obj: Optional[str] = None

    def _help(self) -> str:
        what = f'`{self.obj}` from ' if self.obj else ''
        return f"""
            Failed to import {what} module `{self.module}`.

            Reasons in order of possibility:

            1. `init` command was not called after modifying config
            2. Name of handler module and handler function inside it don't match
            2. Invalid `package` config value, reusing name of existing package
            3. Something's wrong with PYTHONPATH env variable

        """


@dataclass(frozen=True, repr=False)
class ContractAlreadyExistsError(DipDupError):
    """Attemp to add a contract with alias or address which is already in use"""

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


@dataclass(frozen=True, repr=False)
class IndexAlreadyExistsError(DipDupError):
    """Attemp to add an index with alias which is already in use"""

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


@dataclass(frozen=True, repr=False)
class InvalidDataError(DipDupError):
    """Failed to validate datasource message against generated type class"""

    type_cls: Type
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


@dataclass(frozen=True, repr=False)
class CallbackError(DipDupError):
    """An error occured during callback execution"""

    kind: str
    name: str

    def _help(self) -> str:
        return f"""
            `{self.name}` {self.kind} callback execution failed.
        """


@dataclass(frozen=True, repr=False)
class CallbackTypeError(DipDupError):
    """Agrument of invalid type was passed to a callback"""

    kind: str
    name: str

    arg: str
    type_: Type
    expected_type: Type

    def _help(self) -> str:
        return f"""
            `{self.name}` {self.kind} callback was called with an argument of invalid type.

              argument: `{self.arg}`
              type: {self.type_}
              expected type: {self.expected_type}

            Make sure to set correct typenames in config and run `dipdup init --overwrite-types` to regenerate typeclasses.
        """


# TODO: Drop in next major version
@dataclass(frozen=True, repr=False)
class DeprecatedHandlerError(DipDupError):
    """Default handlers need to be converted to hooks"""

    def _help(self) -> str:
        return """
            Default handlers have been deprecated in favor of hooks in DipDup 3.0.

              * `handlers/on_rollback.py` -> `hooks/on_rollback.py`
              * `handlers/on_configure.py` -> `hooks/on_restart.py`
              * [none] -> `hooks/on_reindex.py`

            Perform the following actions:

              1. If you have any custom logic implemented in default handlers move it to corresponding hooks from the table above.
              2. Remove default handlers from project.
        """


@dataclass(frozen=True, repr=False)
class HasuraError(DipDupError):
    """Failed to configure Hasura instance"""

    msg: str

    def _help(self) -> str:
        return f"""
            Failed to configure Hasura: {self.msg}

            GraphQL integration docs: https://docs.dipdup.net/graphql/
        """
