import fileinput
import logging
from typing import Iterable

from dipdup import __spec_version__
from dipdup.codegen import DipDupCodeGenerator
from dipdup.config import DipDupConfig
from dipdup.exceptions import ConfigurationError

deprecated_handlers = ('on_rollback.py', 'on_configure.py')

_logger = logging.getLogger('dipdup.migrations')


class DipDupMigrationManager:
    def __init__(self, config: DipDupConfig, config_paths: Iterable[str]) -> None:
        self._config = config
        self._config_paths = config_paths

    async def migrate(self) -> None:
        # NOTE: We do not need datasources for migration since they are used for jsonschema fetching only
        codegen = DipDupCodeGenerator(self._config, {})

        if self._config.spec_version == __spec_version__:
            _logger.info('Project is already at latest version, no further actions required')

        elif self._config.spec_version == '0.1':
            _logger.warning(
                'Not updating default handlers: deprecated in favor of hooks introduced in 1.2 spec. See release notes for more information.'
            )
            await codegen.migrate_handlers_to_v10()
            self._finish_migration('1.0')

        elif self._config.spec_version == '1.0':
            await codegen.migrate_handlers_to_v11()
            self._finish_migration('1.1')

        elif self._config.spec_version == '1.1':
            await codegen.generate_hooks()
            self._finish_migration('1.2')

        else:
            raise ConfigurationError(f'Unknown `spec_version`, use {__spec_version__} for new projects')

    def _finish_migration(self, spec_version: str) -> None:

        # NOTE: Replace spec_version in config without loading it (to preserve variables)
        for config_path in self._config_paths:
            for line in fileinput.input(config_path, inplace=True):
                if 'spec_version' in line:
                    print(f'spec_version: {spec_version}')
                else:
                    print(line.rstrip())

        _logger.warning('==================== WARNING =====================')
        _logger.warning('Your project has been migrated to spec version %s.', spec_version)
        _logger.warning('Review and commit changes before proceeding.')
        _logger.warning('==================== WARNING =====================')
