import tempfile
import textwrap
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from typing import Dict
from typing import Optional
from typing import Type

import orjson as json
from tabulate import tabulate
from tortoise.models import Model

from dipdup import spec_version_mapping
from dipdup.enums import ReindexingReason

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


def save_crashdump(error: Exception) -> str:
    """Saves a crashdump file with Sentry error data, returns the path to the tempfile"""
    # NOTE: Lazy import to speed up startup
    import sentry_sdk.serializer
    import sentry_sdk.utils

    exc_info = sentry_sdk.utils.exc_info_from_error(error)
    event, _ = sentry_sdk.utils.event_from_exception(exc_info)
    event = sentry_sdk.serializer.serialize(event)

    tmp_dir = Path(tempfile.gettempdir()) / 'dipdup' / 'crashdumps'
    tmp_dir.mkdir(parents=True, exist_ok=True)

    crashdump_file = NamedTemporaryFile(
        mode='ab',
        suffix='.json',
        dir=tmp_dir,
        delete=False,
    )
    with crashdump_file as f:
        f.write(
            json.dumps(
                event,
                option=json.OPT_INDENT_2,
            ),
        )
    return crashdump_file.name


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
        return self.__doc__

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
    def _help(self) -> str:
        ...


@dataclass(repr=False)
class DatasourceError(Error):
    """One of datasources returned an error"""

    msg: str
    datasource: str

    def _help(self) -> str:
        return f"""
            `{self.datasource}` datasource returned an error.
            
            {self.msg}

            See https://docs.dipdup.io/advanced/datasources
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

            See https://docs.dipdup.io/config
        """


@dataclass(repr=False)
class InvalidModelsError(Error):
    """Can't initialize database, `models.py` module is invalid"""

    msg: str
    model: Type[Model]
    field: Optional[str] = None

    def _help(self) -> str:
        return f"""
            {self.msg}

              model: `{self.model._meta._model.__name__}`
              table: `{self.model._meta.db_table}`
              field: `{self.field or ''}`

            See https://docs.dipdup.io/getting-started/defining-models
            See https://docs.dipdup.io/config/database
            See https://docs.dipdup.io/advanced/internal-models
        """


@dataclass(repr=False)
class DatabaseEngineError(Error):
    """Some of the features are not supported with the current database engine"""

    msg: str
    kind: str
    required: str

    def _help(self) -> str:
        return f"""
            {self.msg}

              database: `{self.kind}`
              required: `{self.required}`

            See https://docs.dipdup.io/deployment/database-engines
            See https://docs.dipdup.io/advanced/sql
            See https://docs.dipdup.io/config/database
        """


@dataclass(repr=False)
class MigrationRequiredError(Error):
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
        reindex = '\n\n' + tab + ReindexingRequiredError(ReindexingReason.migration).help() if self.reindex else ''
        return f"""
            Project migration required!

            {version_table.strip()}

            Perform the following actions:

              1. Run `dipdup migrate`.
              2. Review and commit changes.

            See https://docs.dipdup.io/release-notes for more information. {reindex}
        """


@dataclass(repr=False)
class ReindexingRequiredError(Error):
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

            See https://docs.dipdup.io/advanced/reindexing for more information.
        """.format(
            reason=self.reason.value,
            context=context,
        )


@dataclass(repr=False)
class InitializationRequiredError(Error):
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
class ProjectImportError(Error):
    """Can't import type or callback from the project package"""

    module: str
    obj: Optional[str] = None

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
            Contract `{self.name}` (`{self.address}`) already exists.

            Active contracts:

            {contracts_table}
        """


@dataclass(repr=False)
class IndexAlreadyExistsError(Error):
    """Attempt to add an index with an alias already in use"""

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
class InvalidDataError(Error):
    """Failed to validate datasource message against generated type class"""

    msg: str
    type_: Type[Any]
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
class CallbackTypeError(Error):
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

            See https://docs.dipdup.io/getting-started/project-structure
            See https://docs.dipdup.io/cli-reference#init
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

            See https://docs.dipdup.io/graphql/
            See https://docs.dipdup.io/config/hasura
            See https://docs.dipdup.io/cli-reference#dipdup-hasura-configure
        """


@dataclass(repr=False)
class FeatureAvailabilityError(Error):
    """Requested feature is not supported in the current environment"""

    feature: str
    reason: str

    def _help(self) -> str:
        return f"""
            Feature `{self.feature}` is not available in the current environment.

            {self.reason}

            See https://docs.dipdup.io/installation
            See https://docs.dipdup.io/advanced/docker
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


# TODO: Remove in 7.0
DipDupException = FrameworkException
DipDupError = Error
