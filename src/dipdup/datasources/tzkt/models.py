from contextlib import suppress
from functools import lru_cache
from itertools import groupby
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Type

from pydantic import BaseConfig
from pydantic import create_model
from pydantic.error_wrappers import ValidationError
from pydantic.fields import ModelField
from typing_extensions import get_args
from typing_extensions import get_origin

from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import InvalidDataError
from dipdup.models import OperationData
from dipdup.models import StorageType


def _unwrap(storage: Dict[str, Any]) -> Any:
    return storage['wrapped']


def _wrap(storage: Any) -> Dict[str, Any]:
    return {'wrapped': storage}


@lru_cache(None)
def _wrap_type(storage_type: Type[Any]) -> Type[Any]:
    # NOTE: Dark Pydantic magic, see https://github.com/samuelcolvin/pydantic/issues/1937
    wrapped_type: Type = create_model('WrappedStorageType')
    wrapped_type.__fields__['wrapped'] = ModelField(
        name='wrapped',
        type_=storage_type,
        class_validators=None,
        model_config=BaseConfig,
    )
    wrapped_type.__schema_cache__.clear()
    return wrapped_type


@lru_cache(None)
def _unwrap_type(storage_type: Type[Any]) -> Type[Any]:
    return storage_type.__fields__['wrapped'].type_


@lru_cache(None)
def _is_array(storage_type: Type) -> bool:
    """TzKT can return bigmaps as objects or as arrays of key-value objects. We need to guess it from storage type."""
    try:
        fields = storage_type.__fields__
    # NOTE: Not a dataclass
    except AttributeError:
        return False

    # NOTE: TzKT array (dict actually)
    if 'key' in fields and 'value' in fields:
        return True

    # NOTE: Pydantic array
    try:
        return get_origin(get_args(getattr(fields.get('__root__'), 'type_', None))[1]) == list
    except (IndexError, AttributeError):
        return False


@lru_cache(None)
def _extract_field_type(field: Type) -> Type:
    if field.type_ == field.outer_type_:
        return field.type_

    # NOTE: `BaseModel.type_` returns incorrect value when annotation is Dict[str, bool], Dict[str, BaseModel], and possibly in some other cases.
    if field.type_ == bool:
        return field.outer_type_
    with suppress(IndexError, AttributeError):
        get_args(field.outer_type_)[1].__fields__
        return field.outer_type_

    return field.type_


def _preprocess_bigmap_diffs(diffs: Iterable[Dict[str, Any]]) -> Dict[int, Iterable[Dict[str, Any]]]:
    """Filter out bigmap diffs and group them by bigmap id"""
    return {
        k: tuple(v)
        for k, v in groupby(
            filter(lambda d: d['action'] in ('add_key', 'update_key'), diffs),
            lambda d: d['bigmap'],
        )
    }


def _process_storage(
    storage_dict: Dict[str, Any],
    storage_type: Type[StorageType],
    bigmap_diffs: Dict[int, Iterable[Dict[str, Any]]],
) -> None:
    for key, field in storage_type.__fields__.items():
        # NOTE: Plain Pydantic model, ignore
        if key == '__root__':
            continue

        # NOTE: Use field alias when present
        if field.alias:
            key = field.alias

        # NOTE: Ignore missing optional fields, raise on required
        value = storage_dict.get(key)
        if value is None:
            if not field.required:
                continue
            raise ConfigurationError(f'Type `{storage_type.__name__}` is invalid: `{key}` field does not exists')

        field_type = _extract_field_type(field)

        # FIXME: incompatible type "Type[Any]"; expected "Hashable"
        is_array = _is_array(field_type) # type: ignore
        # FIXME: I don't remember why boolean fields are included, but it seems important, do not touch
        is_bigmap_id = field_type not in (int, bool) and isinstance(value, int)
        is_nested_dict = hasattr(field_type, '__fields__') and isinstance(storage_dict[key], dict)
        is_nested_list = hasattr(field_type, '__fields__') and isinstance(storage_dict[key], list)

        if is_bigmap_id:
            storage_dict[key] = [] if is_array else {}

            for diff in bigmap_diffs.get(value, ()):
                bigmap_key, bigmap_value = diff['content']['key'], diff['content']['value']
                if is_array:
                    storage_dict[key].append(  # type: ignore
                        {
                            'key': bigmap_key,
                            'value': bigmap_value,
                        }
                    )
                else:
                    storage_dict[key][bigmap_key] = bigmap_value  # type: ignore

        elif is_nested_dict:
            _process_storage(storage_dict[key], field_type, bigmap_diffs)

        elif is_nested_list:
            for idx, bigmap_id in enumerate(storage_dict[key]):
                storage_dict[key][idx] = [] if is_array else {}

                for diff in bigmap_diffs.get(bigmap_id, ()):
                    bigmap_key, bigmap_value = diff['content']['key'], diff['content']['value']
                    if is_array:
                        storage_dict[key][idx].append(  # type: ignore
                            {
                                'key': bigmap_key,
                                'value': bigmap_value,
                            }
                        )
                    else:
                        storage_dict[key][idx][bigmap_key] = bigmap_value  # type: ignore


def deserialize_storage(operation_data: OperationData, storage_type: Type[StorageType]) -> StorageType:
    """Merge big map diffs and deserialize raw storage into typeclass"""
    bigmap_diffs = _preprocess_bigmap_diffs(operation_data.diffs)
    plain_storage = not isinstance(operation_data.storage, dict)

    if plain_storage:
        storage_type = _wrap_type(storage_type)
        operation_data.storage = _wrap(operation_data.storage)

    _process_storage(
        storage_dict=operation_data.storage,
        storage_type=storage_type,
        bigmap_diffs=bigmap_diffs,
    )

    if plain_storage:
        storage_type = _unwrap_type(storage_type)
        operation_data.storage = _unwrap(operation_data.storage)

    try:
        return storage_type.parse_obj(operation_data.storage)
    except ValidationError as e:
        raise InvalidDataError(
            type_cls=storage_type,
            data=operation_data.storage,
            parsed_object=operation_data,
        ) from e
