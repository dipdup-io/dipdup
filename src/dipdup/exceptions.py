import textwrap
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from tortoise.models import Model

    from dipdup.models import ReindexingReason

tab = ('_' * 80) + '\n\n'


def unindent(text: str) -> str:
    """Remove indentation from text"""
    return textwrap.dedent(text).strip()


def indent(text: str, indent: int = 2) -> str:
    """Add indentation to text"""
    return textwrap.indent(text, ' ' * indent)


def format_help(help: str) -> str:
    """Format help text"""
    return tab + unindent(help) + '\n'


class FrameworkException(AssertionError, RuntimeError):
    pass


class ConfigInitializationException(FrameworkException):
    """Some config preparation stage was skipped. See `DipDupConfig.initialize`."""


class Error(ABC, FrameworkException):
    """Base class for _known_ exceptions in this module.

    Instances of this class should have a nice help message explaining the error and how to fix it.
    """

    def __str__(self) -> str:
        if not self.__doc__:
            raise NotImplementedError(f'{self.__class__.__name__} has no docstring')
        return self.__doc__ + ' -> ' + ' '.join(self.args)

    def help(self) -> str:
        """Return a string containing a help message for this error."""
        return format_help(self._help())

    @classmethod
    def default_help(cls) -> str:
        return format_help(
            """
                An unexpected error has occurred! Most likely it's a framework bug.

                Please, tell us about it: https://github.com/dipdup-io/dipdup/issues
        """
        )

    @abstractmethod
    def _help(self) -> str: ...


@dataclass(repr=False)
class DatasourceError(Error):
    """One of datasources returned an error"""

    msg: str
    datasource: str

    def _help(self) -> str:
        return f"""
            `{self.datasource}` datasource returned an error.
            
            {self.msg}

            See https://dipdup.io/docs/getting-started/datasources
        """


@dataclass(repr=False)
class InvalidRequestError(Error):
    """API returned an unexpected response"""

    msg: str
    url: str

    def _help(self) -> str:
        return f"""
            Unexpected response: {self.msg}

            URL: `{self.url}`

            Make sure that config is correct and you're calling the correct API.
        """


@dataclass(repr=False)
class ConfigurationError(Error):
    """DipDup YAML config is invalid"""

    msg: str

    def _help(self) -> str:
        return f"""
            {self.msg}

            See https://dipdup.io/docs/getting-started/config
        """


@dataclass(repr=False)
class InvalidModelsError(Error):
    """Can't initialize database, `models.py` module is invalid"""

    msg: str
    model: type['Model']
    field: str | None = None

    def _help(self) -> str:
        return f"""
            {self.msg}

              model: `{self.model._meta._model.__name__}`
              table: `{self.model._meta.db_table}`
              field: `{self.field or ''}`

            See https://dipdup.io/docs/getting-started/models
        """


# NOTE: Do not raise this exception directly; call `ctx.reindex` instead!
@dataclass(repr=False)
class ReindexingRequiredError(Error):
    """Unable to continue indexing with existing database"""

    reason: 'ReindexingReason'
    context: dict[str, Any] = field(default_factory=dict)

    def _help(self) -> str:
        # FIXME: Indentation hell
        prefix = '\n' + ' ' * 14
        context = prefix.join(f'{k}: {v}' for k, v in self.context.items())
        if context:
            context = f'{prefix}{context}\n'

        return f"""
            Reindexing required! Reason: {self.reason.value}.
              {context}
            You may want to backup database before proceeding. After that perform one of the following actions:

              - Eliminate the cause of reindexing and run `dipdup schema approve`.
              - Drop database and start indexing from scratch with `dipdup schema wipe` command.

            See https://dipdup.io/docs/advanced/reindexing for more information.
        """


@dataclass(repr=False)
class InitializationRequiredError(Error):
    """Project initialization required"""

    message: str

    def _help(self) -> str:
        return f"""
            Project initialization required! Reason: {self.message}.

            Perform the following actions:

              - Run `dipdup init`.
              - Review and commit changes.
        """


@dataclass(repr=False)
class ProjectImportError(Error):
    """Can't import type or callback from the project package"""

    module: str
    obj: str | None = None

    def _help(self) -> str:
        what = f'`{self.obj}` from ' if self.obj else ''
        return f"""
            Failed to import {what}module `{self.module}`.

            Reasons in order of possibility:

              1. `init` command has not been called after modifying the config
              2. Type or callback has been renamed or removed manually
              3. `package` name is occupied by existing non-DipDup package
              4. Package exists, but not discoverable - check `$PYTHONPATH`
        """


@dataclass(repr=False)
class ContractAlreadyExistsError(Error):
    """Attempt to add a contract with alias or address already in use"""

    name: str

    def _help(self) -> str:
        return f"""
            Contract `{self.name}` already exists in config.
        """


@dataclass(repr=False)
class IndexAlreadyExistsError(Error):
    """Attempt to add an index with an alias already in use"""

    name: str

    def _help(self) -> str:
        return f"""
            Index with name `{self.name}` already exists in config.
        """


@dataclass(repr=False)
class InvalidDataError(Error):
    """Failed to validate datasource message against generated type class"""

    msg: str
    type_: type[Any]
    data: Any

    def _help(self) -> str:
        return f"""
            Failed to validate datasource message against generated type class.

              {self.msg}

            Type class: `{self.type_.__name__}`
            Data: `{self.data}`
        """


@dataclass(repr=False)
class CallbackError(Error):
    """An error occurred during callback execution"""

    module: str
    exc: Exception

    def _help(self) -> str:
        return f"""
            `{self.module}` callback execution failed:

              {self.exc.__class__.__name__}: {self.exc}

            Eliminate the reason of failure and restart DipDup.
        """


@dataclass(repr=False)
class CallbackTypeError(Error):
    """Argument of invalid type was passed to a callback"""

    kind: str
    name: str

    arg: str
    type_: type[Any]
    expected_type: type[Any]

    def _help(self) -> str:
        return f"""
            `{self.name}` {self.kind} callback was called with an argument of invalid type.

              argument: `{self.arg}`
              type: {self.type_}
              expected type: {self.expected_type}

            Make sure to set correct typenames in config and run `dipdup init --force` to regenerate typeclasses.

            See https://dipdup.io/docs/getting-started/package
            See https://dipdup.io/docs/references/cli#init
        """


@dataclass(repr=False)
class HasuraError(Error):
    """Failed to configure Hasura instance"""

    msg: str

    def _help(self) -> str:
        return f"""
            Failed to configure Hasura:

              {self.msg}

            If it's `400 Bad Request`, check out Hasura logs for more information.

            See https://dipdup.io/docs/graphql/hasura
        """


@dataclass(repr=False)
class UnsupportedAPIError(Error):
    """Datasource instance runs an unsupported software version"""

    datasource: str
    host: str
    reason: str

    def _help(self) -> str:
        return f"""
            `{self.host}` API version is not supported by `{self.datasource}` datasource.

            {self.reason}
        """
