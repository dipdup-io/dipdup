import logging
from abc import ABC
from abc import abstractmethod
from collections.abc import Awaitable
from collections.abc import Callable
from pathlib import Path
from shutil import rmtree
from typing import Any

from pydantic import BaseModel

from dipdup.config import CallbackMixin
from dipdup.config import DipDupConfig
from dipdup.datasources import Datasource
from dipdup.exceptions import FrameworkException
from dipdup.package import DEFAULT_ENV
from dipdup.package import KEEP_MARKER
from dipdup.package import PACKAGE_MARKER
from dipdup.package import DipDupPackage
from dipdup.project import render_base
from dipdup.utils import load_template
from dipdup.utils import pascal_to_snake
from dipdup.utils import touch
from dipdup.utils import write
from dipdup.yaml import DipDupYAMLConfig

Callback = Callable[..., Awaitable[None]]
TypeClass = type[BaseModel]

_logger = logging.getLogger(__name__)


class CodeGenerator(ABC):
    def __init__(
        self,
        config: DipDupConfig,
        package: DipDupPackage,
        datasources: dict[str, Datasource[Any]],
        include: set[str] | None = None,
    ) -> None:
        self._config = config
        self._package = package
        self._datasources = datasources
        self._include = include or set()
        self._logger = _logger

    async def init(
        self,
        force: bool = False,
        base: bool = False,
    ) -> None:
        self._package.create()

        replay = self._package.replay
        if base or self._include:
            if not replay:
                raise FrameworkException('`--base` option passed but `configs/replay.yaml` file is missing')
            _logger.info('Recreating base template with replay.yaml')
            render_base(replay, force, self._include)

        if self._include:
            force = any(str(path).startswith('types') for path in self._include)

        await self.generate_abi()
        await self.generate_schemas()
        await self._generate_types(force)

        await self._generate_models()
        await self.generate_hooks()
        await self.generate_system_hooks()
        await self.generate_handlers()

    @abstractmethod
    async def generate_abi(self) -> None: ...

    @abstractmethod
    async def generate_schemas(self) -> None: ...

    @abstractmethod
    async def generate_hooks(self) -> None: ...

    @abstractmethod
    async def generate_system_hooks(self) -> None: ...

    @abstractmethod
    async def generate_handlers(self) -> None: ...

    @abstractmethod
    def get_typeclass_name(self, schema_path: Path) -> str: ...

    async def _generate_types(self, force: bool = False) -> None:
        """Generate typeclasses from fetched JSONSchemas: contract's storage, parameters, big maps and events."""
        for path in self._package.schemas.glob('**/*.json'):
            await self._generate_type(path, force)

    async def _generate_type(self, schema_path: Path, force: bool) -> None:
        rel_path = schema_path.relative_to(self._package.schemas)
        type_pkg_path = self._package.types / rel_path

        if schema_path.is_dir():
            return

        if not schema_path.name.endswith('.json'):
            if schema_path.name != KEEP_MARKER:
                self._logger.warning('Skipping `%s`: not a JSON schema', schema_path)
            return

        module_name = schema_path.stem
        output_path = type_pkg_path.parent / f'{pascal_to_snake(module_name)}.py'
        if output_path.exists() and not force:
            self._logger.debug('Skipping `%s`: type already exists', schema_path)
            return

        import datamodel_code_generator as dmcg

        class_name = self.get_typeclass_name(schema_path)
        self._logger.info('Generating type `%s`', class_name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dmcg.generate(
            input_=schema_path,
            output=output_path,
            class_name=class_name,
            disable_timestamp=True,
            input_file_type=dmcg.InputFileType.JsonSchema,
            target_python_version=dmcg.PythonVersion.PY_311,
            use_union_operator=True,
        )

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

        # FIXME: Missing generic type annotation to comply with `mypy --strict`
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

    async def _generate_models(self) -> None:
        for path in self._package.models.glob('**/*.py'):
            if path.stat().st_size == 0:
                continue
            return

        path = self._package.models / PACKAGE_MARKER
        content_path = Path(__file__).parent.parent / 'templates' / 'models.py'
        write(path, content_path.read_text())

    def _cleanup_schemas(self) -> None:
        rmtree(self._package.schemas)
        self._package.schemas.mkdir()


async def generate_environments(config: DipDupConfig, package: DipDupPackage) -> None:
    for default_env_path in package.deploy.glob(f'*{DEFAULT_ENV}'):
        default_env_path.unlink()

    for config_path in package.configs.iterdir():
        if config_path.suffix not in ('.yml', '.yaml') or not config_path.stem.startswith('dipdup'):
            continue

        config_chain = [
            Path('dipdup.yaml'),
            config_path,
        ]
        _, environment = DipDupYAMLConfig.load(
            paths=config_chain,
            environment=False,
        )
        env_lines = (f'{k}={v}' for k, v in sorted(environment.items()))
        lines: tuple[str, ...] = (
            '# This env file was generated automatically by DipDup. Do not edit it!',
            '# Create a copy with .env extension, fill it with your values and run DipDup with `--env-file` option.',
            '#',
            *env_lines,
            '',
        )
        content = '\n'.join(lines)

        env_filename = config_path.stem.replace('dipdup.', '')
        if env_filename == 'compose':
            env_filename = ''
        env_path = package.deploy / (env_filename + DEFAULT_ENV)
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(content)
