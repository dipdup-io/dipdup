import logging
import re
import subprocess
from abc import ABC
from abc import abstractmethod
from collections import defaultdict
from collections import deque
from pathlib import Path
from shutil import which
from typing import Any
from typing import Awaitable
from typing import Callable

from pydantic import BaseModel

from dipdup.config import CallbackMixin
from dipdup.config import DipDupConfig
from dipdup.datasources import Datasource
from dipdup.exceptions import FeatureAvailabilityError
from dipdup.package import KEEP_MARKER
from dipdup.package import PYTHON_MARKER
from dipdup.package import DipDupPackage
from dipdup.utils import import_submodules
from dipdup.utils import load_template
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal
from dipdup.utils import touch
from dipdup.utils import write

CallbackT = Callable[..., Awaitable[None]]
TypeT = type[BaseModel]


class CodeGenerator(ABC):
    def __init__(
        self,
        config: DipDupConfig,
        package: DipDupPackage,
        datasources: dict[str, Datasource[Any]],
    ) -> None:
        self._config = config
        self._package = package
        self._datasources = datasources
        self._logger = logging.getLogger('dipdup.codegen')

    @abstractmethod
    async def generate_abi(self) -> None:
        ...

    @abstractmethod
    async def generate_schemas(self) -> None:
        ...

    @abstractmethod
    async def generate_types(self, force: bool) -> None:
        ...

    @abstractmethod
    async def generate_hooks(self) -> None:
        ...

    @abstractmethod
    async def generate_event_hooks(self) -> None:
        ...

    @abstractmethod
    async def generate_handlers(self) -> None:
        ...

    @abstractmethod
    def get_typeclass_name(self, schema_path: Path) -> str:
        ...

    async def init(
        self,
        force: bool = False,
    ) -> None:
        self._package.pre_init()
        self._package.create()

        await self.generate_abi()
        await self.generate_schemas()
        await self.generate_types(force)
        await self.generate_type_aliases(force)

        await self.generate_hooks()
        await self.generate_event_hooks()
        await self.generate_handlers()

        self._package.post_init()
        self._package.verify()

    async def generate_type_aliases(self, force: bool) -> None:
        type_aliases_path = self._package.root / 'types' / '__init__.py'
        if not force and (not type_aliases_path.exists() or type_aliases_path.read_text().strip()):
            return

        imports: defaultdict[str, deque[str]] = defaultdict(deque)
        for module in import_submodules(f'{self._package.name}.types').values():
            for obj in module.__dict__.values():
                if isinstance(obj, type) and issubclass(obj, BaseModel) and obj.__name__ != 'BaseModel':
                    imports[obj.__name__].append(module.__name__)

        import_lines: list[str] = []
        for import_name, module_names in imports.items():
            prefix = '' if len(module_names) == 1 else '# '
            if prefix:
                self._logger.info('Type `%s` is defined in multiple modules; skipping alias', import_name)
            for module_name in module_names:
                import_lines.append(f'{prefix}from {module_name} import {import_name}  # noqa: F401')

        write(type_aliases_path, '\n'.join(import_lines), overwrite=True)

    async def _generate_type(self, schema_path: Path, force: bool) -> None:
        rel_path = schema_path.relative_to(self._package.schemas)
        type_pkg_path = self._package.types / rel_path

        if schema_path.is_dir():
            touch(type_pkg_path / PYTHON_MARKER)
            return

        if not schema_path.name.endswith('.json'):
            if schema_path.name != KEEP_MARKER:
                self._logger.warning('Skipping `%s`: not a JSON schema', schema_path)
            return

        module_name = schema_path.stem
        output_path = type_pkg_path.parent / f'{pascal_to_snake(module_name)}.py'
        if output_path.exists() and not force:
            self._logger.info('Skipping `%s`: type already exists', schema_path)
            return

        # NOTE: Skip if the first line starts with "# dipdup: ignore"
        # TODO: Replace with `immune_types` in config
        if output_path.exists():
            with open(output_path) as type_file:
                first_line = type_file.readline()
                if re.match(r'^#\s+dipdup:\s+ignore\s*', first_line):
                    self._logger.info('Skipping `%s`: "# dipdup: ignore" marker found', output_path)
                    return

        datamodel_codegen = which('datamodel-codegen')
        if not datamodel_codegen:
            raise FeatureAvailabilityError(
                feature='codegen',
                reason='datamodel-codegen is not installed. Are you in the `-slim` Docker image? If not - run `dipdup-install`.',
            )

        class_name = self.get_typeclass_name(schema_path)
        class_name = snake_to_pascal(class_name).strip('_')

        self._logger.info('Generating type `%s`', class_name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        (output_path.parent / PYTHON_MARKER).touch(exist_ok=True)
        args = [
            datamodel_codegen,
            '--input',
            str(schema_path),
            '--output',
            str(output_path),
            '--class-name',
            class_name,
            '--disable-timestamp',
        ]
        self._logger.debug(' '.join(args))
        subprocess.run(args, check=True)

    async def _generate_callback(self, callback_config: CallbackMixin, kind: str, sql: bool = False) -> None:
        original_callback = callback_config.callback
        subpackages = callback_config.callback.split('.')
        subpackages, callback = subpackages[:-1], subpackages[-1]

        callback_path = Path(
            self._package.root,
            kind,
            *subpackages,
            f'{callback}.py',
        )

        if callback_path.exists():
            return

        self._logger.info('Generating %s callback `%s`', kind, callback)
        callback_template = load_template('templates', 'callback.py.j2')

        arguments = callback_config.format_arguments()
        imports = set(callback_config.format_imports(self._config.package))

        code: list[str] = []
        if sql:
            code.append(f"await ctx.execute_sql('{original_callback}')")
            if callback == 'on_index_rollback':
                code.append('await ctx.rollback(')
                code.append('    index=index.name,')
                code.append('    from_level=from_level,')
                code.append('    to_level=to_level,')
                code.append(')')
        else:
            code.append('...')

        # NOTE: Fix missing generic type annotation for `Index[IndexConfig]` to comply with `mypy --strict`
        processed_arguments = tuple(
            f'{a},  # type: ignore[type-arg]' if a.startswith('index: Index') else a for a in arguments
        )

        callback_code = callback_template.render(
            callback=callback,
            arguments=tuple(processed_arguments),
            imports=sorted(dict.fromkeys(imports)),
            code=code,
        )
        write(callback_path, callback_code)

        if not sql:
            return

        # NOTE: Preserve the same structure as in `handlers`
        sql_path = Path(
            self._package.sql,
            *subpackages,
            callback,
            KEEP_MARKER,
        )
        touch(sql_path)
