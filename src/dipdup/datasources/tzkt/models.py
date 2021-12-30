from contextlib import suppress
from functools import lru_cache
from itertools import groupby
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Type
from typing import Union

from pydantic.error_wrappers import ValidationError
from pydantic.fields import FieldInfo
from typing_extensions import get_args
from typing_extensions import get_origin

from dipdup.exceptions import InvalidDataError
from dipdup.models import OperationData
from dipdup.models import StorageType

IntrospectionError = (KeyError, IndexError, AttributeError)


def _extract_root_type(storage_type: Type) -> Type:
    """Extract Pydantic __root__ type"""
    return storage_type.__fields__['__root__'].type_


@lru_cache(None)
def _is_array(storage_type: Type) -> bool:
    """TzKT can return bigmaps as objects or as arrays of key-value objects. Guess it from storage type."""
    # NOTE: List[...]
    if get_origin(storage_type) == list:
        return True

    # NOTE: Neither a list not Pydantic model, can't be an array
    fields: Optional[Dict[str, FieldInfo]] = getattr(storage_type, '__fields__', None)
    if fields is None:
        return False

    # NOTE: An item of TzKT array
    if 'key' in fields and 'value' in fields:
        return True

    # NOTE: Pydantic model with __root__ field, dive into it
    with suppress(*IntrospectionError):
        root_type = _extract_root_type(storage_type)
        return _is_array(root_type)  # type: ignore

    # NOTE: Something else
    return False


@lru_cache(None)
def _extract_list_types(storage_type: Type[Any]) -> Iterable[Type[Any]]:
    """Extract list item types from field type"""
    # NOTE: Pydantic model with __root__ field
    with suppress(*IntrospectionError):
        return (_extract_root_type(storage_type),)

    # NOTE: Python list, return all args unpacking unions
    with suppress(*IntrospectionError):
        item_type = get_args(storage_type)[0]
        if get_origin(item_type) == Union:
            return get_args(item_type)
        return (item_type,)

    # NOTE: Something else
    return ()


@lru_cache(None)
def _extract_dict_types(storage_type: Type[Any], key: str) -> Iterable[Type[Any]]:
    """Extract dict value types from field type"""
    # NOTE: Regular dict
    if get_origin(storage_type) == dict:
        return (get_args(storage_type)[1],)

    # NOTE: Unpack union args
    if get_origin(storage_type) == Union:
        return get_args(storage_type)

    # NOTE: Pydantic model, find corresponding field and return it's type
    with suppress(*IntrospectionError):
        fields = storage_type.__fields__
        for field in fields.values():
            if key in (field.name, field.alias):
                return (field.type_,)

    # NOTE: Something else
    return ()


def _preprocess_bigmap_diffs(diffs: Iterable[Dict[str, Any]]) -> Dict[int, Iterable[Dict[str, Any]]]:
    """Filter out bigmap diffs and group them by bigmap id"""
    return {
        k: tuple(v)
        for k, v in groupby(
            filter(lambda d: d['action'] in ('add_key', 'update_key'), diffs),
            lambda d: d['bigmap'],
        )
    }


def _apply_bigmap_diffs(
    bigmap_id: int,
    bigmap_diffs: Dict[int, Iterable[Dict[str, Any]]],
    is_array: bool,
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Apply bigmap diffs to the storage"""
    diffs = bigmap_diffs.get(bigmap_id, ())
    diffs_items = ((d['content']['key'], d['content']['value']) for d in diffs)

    if is_array:
        list_storage: List[Dict[str, Any]] = []
        for key, value in diffs_items:
            list_storage.append({'key': key, 'value': value})
        return list_storage

    else:
        dict_storage: Dict[str, Any] = {}
        for key, value in diffs_items:
            dict_storage[key] = value
        return dict_storage


def _process_storage(
    storage: Any,
    storage_type: Type[StorageType],
    bigmap_diffs: Dict[int, Iterable[Dict[str, Any]]],
) -> Any:
    """Replace bigmap pointers with actual data from diffs"""
    # NOTE: Bigmap pointer, apply diffs
    if isinstance(storage, int) and storage_type not in (int, bool):
        is_array = _is_array(storage_type)
        storage = _apply_bigmap_diffs(storage, bigmap_diffs, is_array)

    # NOTE: List, process recursively
    elif isinstance(storage, list):
        for i, _ in enumerate(storage):
            for item_type in _extract_list_types(storage_type):
                with suppress(*IntrospectionError):
                    storage[i] = _process_storage(storage[i], item_type, bigmap_diffs)

    # NOTE: Dict, process recursively
    elif isinstance(storage, dict):
        for key, value in storage.items():
            for value_type in _extract_dict_types(storage_type, key):
                with suppress(*IntrospectionError):
                    storage[key] = _process_storage(value, value_type, bigmap_diffs)

    else:
        pass

    return storage


def deserialize_storage(operation_data: OperationData, storage_type: Type[StorageType]) -> StorageType:
    """Merge big map diffs and deserialize raw storage into typeclass"""
    bigmap_diffs = _preprocess_bigmap_diffs(operation_data.diffs)

    operation_data.storage = _process_storage(
        storage=operation_data.storage,
        storage_type=storage_type,
        bigmap_diffs=bigmap_diffs,
    )

    try:
        return storage_type.parse_obj(operation_data.storage)
    except ValidationError as e:
        raise InvalidDataError(
            type_cls=storage_type,
            data=operation_data.storage,
            parsed_object=operation_data,
        ) from e
