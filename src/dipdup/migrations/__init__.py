import logging
from abc import abstractmethod
from collections import deque
from pathlib import Path

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

    def _safe_write(self, path: Path, text: str) -> None:
        if self._dry_run:
            _logger.info('Would write to %s:', path)
            _logger.debug(print(text))
        else:
            _logger.info('Writing to %s:', path)
            path.write_text(text)

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

        spec_version = root_config['spec_version']
        if spec_version not in self.from_spec:
            raise MigrationError(f'Unsupported spec version: {spec_version}')

        package_path = env.get_package_path(root_config['package'])
        package = DipDupPackage(package_path)

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

    @abstractmethod
    def migrate_config(self, config: DipDupYAMLConfig) -> DipDupYAMLConfig: ...
