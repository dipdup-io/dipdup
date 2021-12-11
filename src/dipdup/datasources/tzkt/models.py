from typing import Any
from typing import Dict
from typing import Iterable
from typing import Type
from typing import Union

from pydantic.error_wrappers import ValidationError
from typing_extensions import get_args
from typing_extensions import get_origin

from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import InvalidDataError
from dipdup.models import OperationData
from dipdup.models import StorageType

# NOTE: typing_extensions introspection is pretty expensive, let's cache it's results
_is_nested_dict: Dict[Type, bool] = {}


def _unwrap(storage: Dict[str, Any]) -> Any:
    return storage['']


def _wrap(storage: Any) -> Dict[str, Any]:
    return {'': storage}


def _is_array(storage_type) -> bool:
    if not hasattr(storage_type, '__fields__'):
        # NOTE: Not a dataclass
        return False

    f = storage_type.__fields__
    tzkt_array = 'key' in f and 'value' in f
    # FIXME: fuck it (╯°□°）╯︵ ┻━┻)
    try:
        pydantic_array = get_origin(get_args(getattr(f.get('__root__'), 'type_', None))[1]) == list
    except IndexError:
        pydantic_array = False

    return tzkt_array or pydantic_array


def _apply_bigmap_diffs(
    storage_dict: Dict[str, Any],
    bigmap_diffs: Iterable[Dict[str, Any]],
    bigmap_name: str,
    is_array: bool,
) -> None:
    """Apply big map diffs of specific path to storage"""

    for diff in bigmap_diffs:
        bigmap_key: Union[int, str]

        # NOTE: Match by bigmap name
        if diff['path'] == bigmap_name:
            bigmap_key = bigmap_name.split('.')[-1]
            bigmap_dict = storage_dict
        # NOTE: Match by index in plain list storage
        elif diff['path'].isdigit():
            bigmap_key = int(diff['path'])
            bigmap_dict = _unwrap(storage_dict)
        else:
            continue

        key = diff['content']['key']
        if is_array:
            bigmap_dict[bigmap_key].append(  # type: ignore
                {
                    'key': key,
                    'value': diff['content']['value'],
                }
            )
        else:
            bigmap_dict[bigmap_key][key] = diff['content']['value']  # type: ignore


def _process_storage(
    storage_dict: Dict[str, Any],
    storage_type: Type[StorageType],
    bigmap_diffs: Iterable[Dict[str, Any]],
    prefix: str = None,
) -> None:
    for key, field in storage_type.__fields__.items():
        if key == '__root__':
            continue

        if field.alias:
            key = field.alias

        bigmap_name = key if prefix is None else f'{prefix}.{key}'

        # NOTE: TzKT could return bigmaps as object or as array of key-value objects. We need to guess this from storage.
        if (value := storage_dict.get(key)) is None:
            if not field.required:
                continue
            raise ConfigurationError(f'Type `{storage_type.__name__}` is invalid: `{key}` field does not exists')

        # NOTE: Pydantic bug? I have no idea how does it work, this workaround is just a guess.
        # NOTE: `BaseModel.type_` returns incorrect value when annotation is Dict[str, bool], Dict[str, BaseModel], and possibly any other cases.
        is_complex_type = field.type_ != field.outer_type_
        is_nested_dict_model = _is_nested_dict.get(field.outer_type_)
        if is_nested_dict_model is None:
            try:
                get_args(field.outer_type_)[1].__fields__
                is_nested_dict_model = _is_nested_dict[field.outer_type_] = True
            except Exception:
                is_nested_dict_model = _is_nested_dict[field.outer_type_] = False

        if is_complex_type and (field.type_ == bool or is_nested_dict_model):
            field_type = field.outer_type_
        else:
            field_type = field.type_

        if field_type not in (int, bool) and isinstance(value, int):
            is_array = _is_array(field_type)
            storage_dict[key] = [] if is_array else {}
            _apply_bigmap_diffs(storage_dict, bigmap_diffs, bigmap_name, is_array)

        elif hasattr(field_type, '__fields__') and isinstance(storage_dict[key], dict):
            _process_storage(storage_dict[key], field_type, bigmap_diffs, bigmap_name)


def _process_plain_storage(
    storage_dict: Dict[str, Any],
    storage_type: Type[StorageType],
    bigmap_diffs: Iterable[Dict[str, Any]],
) -> None:
    # NOTE: Plain storage is either an empty model with `Extra.allow` or one with `__root__: list`
    is_array = _is_array(storage_type)
    unwrapped_storage = _unwrap(storage_dict)

    # NOTE: Replace bigmap ids with empty structures
    if isinstance(unwrapped_storage, int):
        storage_dict[''] = [] if is_array else {}

    elif isinstance(unwrapped_storage, list):
        for i, item in enumerate(unwrapped_storage):
            if isinstance(item, int):
                unwrapped_storage[i] = [] if is_array else {}

    _apply_bigmap_diffs(storage_dict, bigmap_diffs, '', is_array)


def deserialize_storage(operation_data: OperationData, storage_type: Type[StorageType]) -> StorageType:
    """Merge big map diffs and deserialize raw storage into typeclass"""
    diffs = tuple(d for d in operation_data.diffs if d['action'] in ('add_key', 'update_key'))

    if isinstance(operation_data.storage, dict):
        _process_storage(
            storage_dict=operation_data.storage,
            storage_type=storage_type,
            bigmap_diffs=diffs,
            prefix=None,
        )

    elif isinstance(operation_data.storage, (int, list)):
        # NOTE: TzKT returns empty string path for storage root, this hack allows to threat it as a regular dict storage
        operation_data.storage = _wrap(operation_data.storage)
        _process_plain_storage(
            storage_dict=operation_data.storage,
            storage_type=storage_type,
            bigmap_diffs=diffs,
        )
        operation_data.storage = _unwrap(operation_data.storage)

    else:
        raise RuntimeError('Storage type must be one of `dict`, `list` or `int`')

    try:
        return storage_type.parse_obj(operation_data.storage)
    except ValidationError as e:
        raise InvalidDataError(
            type_cls=storage_type,
            data=operation_data.storage,
            parsed_object=operation_data,
        ) from e
