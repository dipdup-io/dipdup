import logging
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Type
from typing import TypeVar
from typing import Union

from pydantic import BaseModel
from pydantic import ValidationError

from dipdup.exceptions import InvalidDataError

if TYPE_CHECKING:
    from jinja2 import Template

_logger = logging.getLogger('dipdup.codegen')


def touch(path: Path) -> None:
    """Create empty file, ignore if already exists"""
    if not path.parent.exists():
        _logger.info('Creating directory `%s`', path.parent)
        path.parent.mkdir(parents=True, exist_ok=True)

    if not path.is_file():
        _logger.info('Creating file `%s`', path)
        path.touch()


def write(path: Path, content: Union[str, bytes], overwrite: bool = False) -> bool:
    """Write content to file, create directory tree if necessary"""
    if not path.parent.exists():
        _logger.info('Creating directory `%s`', path.parent)
        path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and not overwrite:
        return False

    _logger.info('Writing into file `%s`', path)
    if isinstance(content, str):
        content = content.encode()
    path.write_bytes(content)
    return True


@cache
def load_template(*path: str) -> 'Template':
    """Load template from path relative to dipdup package"""
    from jinja2 import Template

    full_path = Path(__file__).parent.parent.joinpath(*path)
    return Template(full_path.read_text())


ObjectT = TypeVar('ObjectT', bound=BaseModel)


def parse_object(type_: Type[ObjectT], data: Any) -> ObjectT:
    try:
        return type_.parse_obj(data)
    except ValidationError as e:
        msg = f'Failed to parse: {e.errors()}'
        raise InvalidDataError(msg, type_, data) from e
