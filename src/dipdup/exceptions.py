import textwrap
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Optional, Type

from tabulate import tabulate

from dipdup import spec_version_mapping

_tab = '\n\n' + ('_' * 80) + '\n\n'


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


@dataclass(frozen=True)
class DipDupError(Exception):
    """Unknown DipDup error"""

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}: {self.__doc__}'

    def _help(self) -> str:
        return """
            Unexpected error occurred!

            Please file a bug report at https://github.com/dipdup-net/dipdup/issues and attach the following:

              * `dipdup.yml` config. Make sure to remove sensitive information.
              * Reasonable amount of logs before the crash.
        """

    def help(self) -> str:
        return unindent(self._help())

    def format(self) -> str:
        exc = f'\n\n{traceback.format_exc()}'.rstrip()
        return _tab.join([exc, self.help() + '\n'])

    @contextmanager
    def wrap(ctx: Optional[Any] = None) -> Iterator[None]:
        try:
            yield
        except DipDupError:
            raise
        except Exception as e:
            raise DipDupError from e


@dataclass(frozen=True)
class ConfigurationError(DipDupError):
    """DipDup YAML config is invalid"""

    msg: str

    def _help(self) -> str:
        return f"""
            {self.msg}

            DipDup config reference: https://docs.dipdup.net/config-file-reference
        """


@dataclass(frozen=True)
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
        return f"""
            Project migration required!

            {version_table}

              1. Run `dipdup migrate`
              2. Review and commit changes

            See https://baking-bad.org/blog/ for additional release information.

            {_tab + ReindexingRequiredError().help() if self.reindex else ''}
        """


@dataclass(frozen=True)
class ReindexingRequiredError(DipDupError):
    """Performed migration requires reindexing"""

    def _help(self) -> str:
        return """
            Reindexing required!

            Recent changes in the framework have made it necessary to reindex the project.

              1. Optionally backup a database
              2. Run `dipdup run --reindex` 
        """


@dataclass(frozen=True)
class InitializationRequiredError(DipDupError):
    def _help(self) -> str:
        return """
            Project initialization required!

            1. Run `dipdup init`
            2. Review and commit changes
        """


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class IndexAlreadyExistsError(DipDupError):
    """Attemp to add an index with alias which is already in use"""

    ctx: Any
    name: str

    def format_help(self) -> str:
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


@dataclass(frozen=True)
class InvalidDataError(DipDupError):
    """Failed to validate operation/big_map data against a generated type class"""

    type_cls: Type
    data: Any
    parsed_object: Any

    def _help(self) -> str:

        return f"""
            Failed to validate operation/big_map data against a generated type class.

            Expected type:
            `{self.type_cls.__class__.__qualname__}`

            Invalid data:
            {self.data}

            Parsed object:
            {self.parsed_object}
        """


@dataclass(frozen=True)
class CallbackError(DipDupError):
    """An error occured during callback execution"""

    name: str
    kind: str

    def _help(self) -> str:
        return f"""
            `{self.name}` {self.kind} callback execution failed.
        """


@dataclass(frozen=True)
class CallbackTypeError(DipDupError):
    """Agrument of invalid type was passed to a callback"""

    name: str
    kind: str

    arg: str
    type_: Type
    expected_type: Type

    def _help(self) -> str:
        return f"""
            `{self.name}` {self.kind} callback was called with an argument of invalid type.

              argument: `{self.arg}`
              type: {self.type_}
              expected type: {self.expected_type}
        """


@dataclass(frozen=True)
class CallbackNotImplementedError(DipDupError):
    # NOTE: Optionals to raise from callbacks without arguments. Will be wrapped.
    kind: str = ''
    name: str = ''

    def _help(self) -> str:
        return f"""
            `{self.name}` {self.kind} callback is not implemented.

            If you want this {self.kind} to present in config but do nothing, remove `raise` statement from it.
        """
