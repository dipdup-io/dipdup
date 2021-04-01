from contextlib import suppress
import logging
from os import mkdir
import os
from os.path import dirname, exists, join
import subprocess

from jinja2 import Template
from pytezos_dapps.config import PytezosDappConfig

_logger = logging.getLogger(__name__)

def fetch_schemas():
    ...

def generate_types(config: PytezosDappConfig):
    schemas_path = join(config.package_path, 'schemas')
    types_path = join(config.package_path, 'types')

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

def generate_handlers(config: PytezosDappConfig):

    _logger.info('Loading handler template')
    with open(join(dirname(__file__), 'handler.py.j2')) as file:
        template = Template(file.read())

    _logger.info('Creating handlers package')
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
