import logging
import os
import subprocess
from contextlib import suppress
from os import mkdir
from os.path import dirname, exists, join

from jinja2 import Template

from dipdup.config import DipDupConfig

_logger = logging.getLogger(__name__)


def create_package(config: DipDupConfig):
    try:
        package_path = config.package_path
    except ImportError:
        package_path = join(os.getcwd(), config.package)
        mkdir(package_path)
        with open(join(package_path, '__init__.py'), 'w'):
            pass

    models_path = join(package_path, 'models.py')
    if not exists(models_path):
        with open(join(dirname(__file__), 'templates', 'models.py.j2')) as file:
            template = Template(file.read())
        models_code = template.render()
        with open(models_path, 'w') as file:
            file.write(models_code)


def fetch_schemas():
    ...


def generate_types(config: DipDupConfig):
    schemas_path = join(config.package_path, 'schemas')
    types_path = join(config.package_path, 'types')

    _logger.info('Creating `types` package')
    with suppress(FileExistsError):
        mkdir(types_path)
        with open(join(types_path, '__init__.py'), 'w'):
            pass

    for root, dirs, files in os.walk(schemas_path):
        types_root = root.replace(schemas_path, types_path)

        for dir in dirs:
            dir_path = join(types_root, dir)
            with suppress(FileExistsError):
                os.mkdir(dir_path)
                with open(join(dir_path, '__init__.py'), 'w'):
                    pass

        for file in files:
            if not file.endswith('.json'):
                continue
            entrypoint_name = file[:-5]
            entrypoint_name_titled = entrypoint_name.title().replace('_', '')

            input_path = join(root, file)
            output_path = join(types_root, f'{entrypoint_name}.py')
            _logger.info('Generating parameter type for entrypoint `%s`', entrypoint_name)
            subprocess.run(
                [
                    'datamodel-codegen',
                    '--input',
                    input_path,
                    '--output',
                    output_path,
                    '--class-name',
                    entrypoint_name_titled,
                    '--disable-timestamp',
                ],
                check=True,
            )


def generate_handlers(config: DipDupConfig):

    _logger.info('Loading handler template')
    with open(join(dirname(__file__), 'templates', 'handler.py.j2')) as file:
        template = Template(file.read())

    _logger.info('Creating `handlers` package')
    handlers_path = join(config.package_path, 'handlers')
    with suppress(FileExistsError):
        mkdir(handlers_path)
        with open(join(handlers_path, '__init__.py'), 'w'):
            pass

    for index in config.indexes.values():
        if not index.operation:
            continue
        for handler in index.operation.handlers:
            _logger.info('Generating handler `%s`', handler.callback)
            handler_code = template.render(
                package=config.package,
                handler=handler.callback,
                patterns=handler.pattern,
            )
            handler_path = join(handlers_path, f'{handler.callback}.py')
            if not exists(handler_path):
                with open(handler_path, 'w') as file:
                    file.write(handler_code)
