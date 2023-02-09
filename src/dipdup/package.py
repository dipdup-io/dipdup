from pathlib import Path

from dipdup.exceptions import ProjectImportError

# from dipdup.utils import import_from
# from dipdup.utils import pascal_to_snake
# from dipdup.utils import snake_to_pascal
from dipdup.utils import touch

# from typing import Awaitable
# from typing import Callable
# from typing import cast

# from pydantic import BaseModel


KEEP_MARKER = '.keep'
PYTHON_MARKER = '__init__.py'
PEP_561_MARKER = 'py.typed'
MODELS_MODULE = 'models.py'


class DipDupPackage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.package = root.name
        self.schemas = root / 'schemas'
        self.types = root / 'types'
        self.handlers = root / 'handlers'
        self.hooks = root / 'hooks'
        self.sql = root / 'sql'
        self.graphql = root / 'graphql'
        self.abi = root / 'abi'

    def create(self) -> None:
        """Create Python package skeleton if not exists"""
        if self.root.exists() and not self.root.is_dir():
            raise ProjectImportError(f'`{self.root}` is not a valid DipDup package path')

        touch(self.root / PYTHON_MARKER)
        touch(self.root / PEP_561_MARKER)
        touch(self.root / MODELS_MODULE)

        touch(self.types / PYTHON_MARKER)
        touch(self.handlers / PYTHON_MARKER)
        touch(self.hooks / PYTHON_MARKER)

        touch(self.sql / KEEP_MARKER)
        touch(self.graphql / KEEP_MARKER)
        touch(self.abi / KEEP_MARKER)

    # def get_storage_type(self, typename: str) -> type[BaseModel]:
    #     cls_name = snake_to_pascal(typename) + 'Storage'
    #     module_name = f'{self.package}.types.{typename}.storage'
    #     return cast(
    #         type[BaseModel],
    #         import_from(module_name, cls_name),
    #     )

    # def get_parameter_type(self, typename: str, entrypoint: str) -> type[BaseModel]:
    #     entrypoint = entrypoint.lstrip('_')
    #     module_name = f'{self.package}.types.{typename}.parameter.{pascal_to_snake(entrypoint)}'
    #     cls_name = snake_to_pascal(entrypoint) + 'Parameter'
    #     return cast(
    #         type[BaseModel],
    #         import_from(module_name, cls_name),
    #     )

    # def get_event_type(self, typename: str, tag: str) -> type[BaseModel]:
    #     tag = pascal_to_snake(tag.replace('.', '_'))
    #     module_name = f'{self.package}.types.{typename}.event.{tag}'
    #     cls_name = snake_to_pascal(f'{tag}_payload')
    #     return cast(
    #         type[BaseModel],
    #         import_from(module_name, cls_name),
    #     )

    # def get_big_map_key_type(self, typename: str, path: str) -> type[BaseModel]:
    #     path = pascal_to_snake(path.replace('.', '_'))
    #     module_name = f'{self.package}.types.{typename}.big_map.{path}_key'
    #     cls_name = snake_to_pascal(path + '_key')
    #     return cast(
    #         type[BaseModel],
    #         import_from(module_name, cls_name),
    #     )

    # def get_big_map_value_type(self, typename: str, path: str) -> type[BaseModel]:
    #     path = pascal_to_snake(path.replace('.', '_'))
    #     module_name = f'{self.package}.types.{typename}.big_map.{path}_value'
    #     cls_name = snake_to_pascal(path + '_value')
    #     return cast(
    #         type[BaseModel],
    #         import_from(module_name, cls_name),
    #     )

    # def get_callback_fn(self, kind: str, callback: str) -> Callable[..., Awaitable[None]]:
    #     module_name = f'{self.package}.{kind}s.{callback}'
    #     fn_name = callback.rsplit('.', 1)[-1]
    #     return cast(
    #         Callable[..., Awaitable[None]],
    #         import_from(module_name, fn_name),
    #     )
