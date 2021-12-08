from typing import Any
from typing import Dict
from typing import List
from typing import Type

from pydantic.error_wrappers import ValidationError
from typing_extensions import get_args

from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import InvalidDataError
from dipdup.models import OperationData
from dipdup.models import StorageType

# NOTE: typing_extensions introspection is pretty expensive
_is_nested_dict: Dict[Type, bool] = {}


def _apply_bigmap_diffs(
    storage_dict: Dict[str, Any],
    bigmap_diffs: List[Dict[str, Any]],
    bigmap_name: str,
    is_array: bool,
) -> None:
    """Apply big map diffs of specific path to storage"""
    bigmap_key = bigmap_name.split('.')[-1]
    for diff in bigmap_diffs:
        if diff['path'] != bigmap_name:
            continue
        if diff['action'] not in ('add_key', 'update_key'):
            continue

        key = diff['content']['key']
        if is_array:
            storage_dict[bigmap_key].append(
                {
                    'key': key,
                    'value': diff['content']['value'],
                }
            )
        else:
            storage_dict[bigmap_key][key] = diff['content']['value']


def _process_storage(
    storage_dict: Dict[str, Any],
    storage_type: Type[StorageType],
    bigmap_diffs: List[Dict[str, Any]],
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
            annotation = field.outer_type_
        else:
            annotation = field.type_

        if annotation not in (int, bool) and isinstance(value, int):
            is_array = hasattr(annotation, '__fields__') and 'key' in annotation.__fields__ and 'value' in annotation.__fields__
            storage_dict[key] = [] if is_array else {}
            _apply_bigmap_diffs(storage_dict, bigmap_diffs, bigmap_name, is_array)

        elif hasattr(annotation, '__fields__') and isinstance(storage_dict[key], dict):
            _process_storage(storage_dict[key], annotation, bigmap_diffs, bigmap_name)


def _process_plain_storage(
    storage_dict: Dict[str, Any],
    storage_type: Type[StorageType],
    bigmap_diffs: List[Dict[str, Any]],
):
    # NOTE: Plain storage is either an empty model with `Extra.allow` or `__root__: list`
    is_array = '__root__' in storage_type.__fields__
    storage_dict[''] = [] if is_array else {}
    _apply_bigmap_diffs(storage_dict, bigmap_diffs, '', is_array)


def deserialize_storage(operation_data: OperationData, storage_type: Type[StorageType]) -> StorageType:
    """Merge big map diffs and deserialize raw storage into typeclass"""
    if isinstance(operation_data.storage, dict):
        _process_storage(
            storage_dict=operation_data.storage,
            storage_type=storage_type,
            bigmap_diffs=operation_data.diffs or [],
            prefix=None,
        )

    elif isinstance(operation_data.storage, int):
        operation_data.storage = {'': operation_data.storage}
        _process_plain_storage(
            storage_dict=operation_data.storage,
            storage_type=storage_type,
            bigmap_diffs=operation_data.diffs or [],
        )
        operation_data.storage = operation_data.storage['']

    else:
        raise RuntimeError

    try:
        return storage_type.parse_obj(operation_data.storage)
    except ValidationError as e:
        raise InvalidDataError(
            type_cls=storage_type,
            data=operation_data.storage,
            parsed_object=operation_data,
        ) from e
