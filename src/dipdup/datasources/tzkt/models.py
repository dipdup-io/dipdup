from contextlib import suppress
from functools import lru_cache
from itertools import groupby
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Type
from typing import Union
from typing import cast

from pydantic.error_wrappers import ValidationError
from typing_extensions import get_args
from typing_extensions import get_origin

from dipdup.exceptions import InvalidDataError
from dipdup.models import OperationData
from dipdup.models import StorageType

IntrospectionError = (KeyError, IndexError, AttributeError)


def _get_root_type(storage_type: Type) -> Type:
    return storage_type.__fields__['__root__'].type_


@lru_cache(None)
def _is_array(storage_type: Type) -> bool:
    """TzKT can return bigmaps as objects or as arrays of key-value objects. Guess it from storage type."""
    if get_origin(storage_type) == list:
        return True

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
        root_type = _get_root_type(storage_type)
        return _is_array(root_type)  # type: ignore
    except IntrospectionError:
        return False


@lru_cache(None)
def _extract_list_types(storage_type: Type[Any]) -> Iterable[Type[Any]]:
    # NOTE: Pydantic model with list root
    with suppress(*IntrospectionError):
        return (_get_root_type(storage_type),)

    # NOTE: Python list
    with suppress(*IntrospectionError):
        item_type = get_args(storage_type)[0]
        if get_origin(item_type) == Union:
            return get_args(item_type)
        return (item_type,)

    # NOTE: Something else
    return ()


@lru_cache(None)
def _extract_dict_types(storage_type: Type[Any], key: str) -> Iterable[Type[Any]]:
    if get_origin(storage_type) == dict:
        return (get_args(storage_type)[1],)

    if get_origin(storage_type) == Union:
        return get_args(storage_type)

    with suppress(*IntrospectionError):
        fields = storage_type.__fields__
        for field in fields.values():
            if key in (field.name, field.alias):
                return (field.type_,)

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
    storage: Union[List[Dict[str, Any]], Dict[str, Any]] = [] if is_array else {}
    for diff in bigmap_diffs.get(bigmap_id, ()):
        bigmap_key, bigmap_value = diff['content']['key'], diff['content']['value']
        if is_array:
            cast(list, storage).append(
                {
                    'key': bigmap_key,
                    'value': bigmap_value,
                }
            )
        else:
            storage[bigmap_key] = bigmap_value

    return storage


def _process_storage(
    storage: Any,
    storage_type: Type[StorageType],
    bigmap_diffs: Dict[int, Iterable[Dict[str, Any]]],
) -> Any:
    # NOTE: Bigmap pointer, apply diffs
    if isinstance(storage, int) and storage_type not in (int, bool):
        is_array = _is_array(storage_type)
        storage = _apply_bigmap_diffs(storage, bigmap_diffs, is_array)

    # NOTE: List of something, apply diffs recursively if needed
    elif isinstance(storage, list):
        for i, _ in enumerate(storage):
            for item_type in _extract_list_types(storage_type):
                with suppress(*IntrospectionError):
                    storage[i] = _process_storage(storage[i], item_type, bigmap_diffs)

    # NOTE: Regular dict, possibly nested: fire up introspection magic
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
