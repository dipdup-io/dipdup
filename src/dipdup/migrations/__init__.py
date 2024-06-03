import logging
from abc import abstractmethod
from collections import deque
from pathlib import Path
from shutil import rmtree

from dipdup import env
from dipdup.exceptions import MigrationError
from dipdup.package import DipDupPackage
from dipdup.yaml import DipDupYAMLConfig

_logger = logging.getLogger(__name__)


class ProjectMigration:
    from_spec: tuple[str, ...]
    to_spec: str

    def __init__(
        self,
        config_paths: tuple[Path, ...],
        dry_run: bool = False,
    ) -> None:
        self._config_paths = config_paths
        self._dry_run = dry_run

    # TODO: Move to utils
    def _safe_write(self, path: Path, text: str) -> None:
        if self._dry_run:
            _logger.info('Would write to %s', path)
        else:
            _logger.info('Writing to %s', path)
            path.write_text(text)

    def _safe_remove(self, path: Path) -> None:
        if self._dry_run:
            _logger.info('Would remove %s', path)
        else:
            _logger.info('Removing %s', path)
            rmtree(path)

    def _safe_rename(self, path: Path, new_path: Path) -> None:
        if self._dry_run:
            _logger.info('Would rename %s to %s', path, new_path)
        else:
            _logger.info('Renaming %s to %s', path, new_path)
            path.rename(new_path)

    def migrate(self) -> None:
        root_config_path = self._config_paths[0]
        if root_config_path.is_dir():
            root_config_path /= 'dipdup.yaml'
        root_config, _ = DipDupYAMLConfig.load(
            paths=[root_config_path],
            environment=False,
            raw=True,
        )

        if 'package' not in root_config or 'spec_version' not in root_config:
            raise MigrationError('Missing config header (package, spec_version fields)')

        package_path = env.get_package_path(root_config['package'])
        package = DipDupPackage(package_path)

        if package.in_migration():
            raise MigrationError('Project is already in migration')

        spec_version = root_config['spec_version']
        if str(spec_version) not in self.from_spec:
            raise MigrationError(f'Unsupported spec version: {spec_version}')

        _logger.info('Migrating project `%s`: %s -> %s', package.name, self.from_spec, self.to_spec)

        root_config = self.migrate_config(root_config)
        self._safe_write(root_config_path, root_config.dump())

        child_config_paths: deque[Path] = deque(self._config_paths[1:])
        for path in package.configs.glob('**/dipdup*.y[a]ml'):
            if path not in child_config_paths:
                child_config_paths.append(path)

        _logger.info('Found %s partial configs', len(child_config_paths))

        for path in child_config_paths:
            config, _ = DipDupYAMLConfig.load(
                paths=[path],
                environment=False,
                raw=True,
            )
            config['package'] = (package.name,)
            config['spec_version'] = self.to_spec

            config = self.migrate_config(config)

            config.pop('package')
            config.pop('spec_version')

            self._safe_write(path, config.dump())

        self.migrate_code(package)

    @abstractmethod
    def migrate_config(self, config: DipDupYAMLConfig) -> DipDupYAMLConfig: ...

    def migrate_code(self, package: DipDupPackage) -> None:
        if package.in_migration():
            raise MigrationError('Project is already in migration')

        if package.handlers.exists():
            self._safe_rename(package.handlers, package.root / 'handlers.old')
        if package.hooks.exists():
            self._safe_rename(package.hooks, package.root / 'hooks.old')
        if package.types.exists():
            self._safe_remove(package.types)
