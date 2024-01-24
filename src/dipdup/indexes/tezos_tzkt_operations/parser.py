from collections.abc import Hashable
from collections.abc import Iterable
from contextlib import suppress
from functools import lru_cache
from itertools import groupby
from types import UnionType
from typing import Any
from typing import TypeVar
from typing import Union
from typing import cast
from typing import get_args
from typing import get_origin

from pydantic import BaseModel
from pydantic import Extra

from dipdup.exceptions import InvalidDataError
from dipdup.models.tezos_tzkt import TzktOperationData
from dipdup.utils import parse_object

StorageType = TypeVar('StorageType', bound=BaseModel)


IntrospectionError = (KeyError, IndexError, AttributeError)

T = TypeVar('T', Hashable, type[BaseModel])


def extract_root_outer_type(storage_type: type[BaseModel]) -> T:  # type: ignore[type-var]
    """Extract Pydantic __root__ type"""
    root_field = storage_type.__fields__['__root__']
    if root_field.allow_none:
        # NOTE: Optional is a magic _SpecialForm
        return cast(type[BaseModel], root_field.type_ | None)

    return root_field.outer_type_  # type: ignore[no-any-return]


def is_array_type(storage_type: type[Any]) -> bool:
    """TzKT can return bigmaps as objects or as arrays of key-value objects. Guess it from storage type."""
    # NOTE: list[...]
    if get_origin(storage_type) == list:
        return True

    # NOTE: Pydantic model with __root__ field subclassing List
    with suppress(*IntrospectionError):
        root_type = extract_root_outer_type(storage_type)
        return is_array_type(root_type)

    # NOTE: Something else
    return False


def get_list_elt_type(list_type: type[Any]) -> type[Any]:
    """Extract list item type from list type"""
    # NOTE: regular list
    if get_origin(list_type) == list:
        return get_args(list_type)[0]  # type: ignore[no-any-return]

    # NOTE: Pydantic model with __root__ field subclassing List
    root_type = extract_root_outer_type(list_type)
    return get_list_elt_type(root_type)


def get_dict_value_type(dict_type: type[Any], key: str | None = None) -> type[Any]:
    """Extract dict value types from field type"""
    # NOTE: Regular dict
    if get_origin(dict_type) == dict:
        return get_args(dict_type)[1]  # type: ignore[no-any-return]

    # NOTE: Pydantic model with __root__ field subclassing Dict
    with suppress(*IntrospectionError):
        root_type = extract_root_outer_type(dict_type)
        return get_dict_value_type(root_type, key)

    if key is None:
        raise KeyError('Field name or alias is required for object introspection')

    # NOTE: Pydantic model, find corresponding field and return it's type
    fields = dict_type.__fields__
    for field in fields.values():
        if key in (field.name, field.alias):
            # NOTE: Pydantic does not preserve outer_type_ for Optional
            if field.allow_none:
                return cast(type[Any], field.type_ | None)
            return field.outer_type_  # type: ignore[no-any-return]

    # NOTE: Either we try the wrong Union path or model was modifier by user
    raise KeyError(f'Field `{key}` not found in {dict_type}')


def unwrap_union_type(union_type: type[Any]) -> tuple[bool, tuple[type[Any], ...]]:
    """Check if the type is either optional or union and return arg types if so"""
    if isinstance(union_type, UnionType):
        return True, union_type.__args__
    if get_origin(union_type) == Union:
        return True, get_args(union_type)

    with suppress(*IntrospectionError):
        root_type = extract_root_outer_type(union_type)
        return unwrap_union_type(root_type)

    return False, ()


def _preprocess_bigmap_diffs(diffs: Iterable[dict[str, Any]]) -> dict[int, Iterable[dict[str, Any]]]:
    """Filter out bigmap diffs and group them by bigmap id"""
    return {
        k: tuple(v)
        for k, v in groupby(
            filter(lambda d: d['action'] in ('add_key', 'update_key'), diffs),
            lambda d: cast(int, d['bigmap']),
        )
    }


def _apply_bigmap_diffs(
    bigmap_id: int,
    bigmap_diffs: dict[int, Iterable[dict[str, Any]]],
    is_array: bool,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Apply bigmap diffs to the storage"""
    diffs = bigmap_diffs.get(bigmap_id, ())
    diffs_items = ((d['content']['key'], d['content']['value']) for d in diffs)

    if is_array:
        list_storage: list[dict[str, Any]] = []
        for key, value in diffs_items:
            list_storage.append({'key': key, 'value': value})
        return list_storage

    dict_storage: dict[str, Any] = {}
    for key, value in diffs_items:
        dict_storage[key] = value
    return dict_storage


def _process_storage(storage: Any, storage_type: T, bigmap_diffs: dict[int, Iterable[dict[str, Any]]]) -> Any:
    """Replace bigmap pointers with actual data from diffs"""
    storage_type = cast(type[BaseModel], storage_type)  # type: ignore[redundant-cast]
    # NOTE: First, check if the type is a Union. Remember, Optional is a Union too.
    is_union, arg_types = unwrap_union_type(storage_type)
    if is_union:
        # NOTE: We have no way but trying every possible branch until first success
        for arg_type in arg_types:
            with suppress(*IntrospectionError):
                return _process_storage(storage, arg_type, bigmap_diffs)

    # NOTE: Value is a bigmap pointer; apply diffs according to array type
    if isinstance(storage, int) and type(storage) != storage_type:
        is_array = is_array_type(storage_type)
        storage = _apply_bigmap_diffs(storage, bigmap_diffs, is_array)

    # NOTE: List, process recursively
    elif isinstance(storage, list):
        elt_type = get_list_elt_type(storage_type)
        for i, _ in enumerate(storage):
            storage[i] = _process_storage(storage[i], elt_type, bigmap_diffs)

    # NOTE: Dict, process recursively
    elif isinstance(storage, dict):
        # NOTE: Ignore missing fields along with extra ones
        ignore = getattr(getattr(storage_type, 'Config', None), 'extra', None) == Extra.ignore

        for key, value in storage.items():
            try:
                value_type = get_dict_value_type(storage_type, key)
                storage[key] = _process_storage(value, value_type, bigmap_diffs)
            except IntrospectionError:
                if not ignore:
                    raise
    # NOTE: Leave others untouched
    else:
        pass

    return storage


def deserialize_storage(
    operation_data: TzktOperationData,
    storage_type: type[StorageType],
) -> tuple[TzktOperationData, StorageType]:
    """Merge big map diffs and deserialize raw storage into typeclass"""
    bigmap_diffs = _preprocess_bigmap_diffs(operation_data.diffs)

    try:
        # NOTE: op data is frozen, repack in-place 🥶
        operation_data_dict = operation_data.__dict__
        operation_data_dict['storage'] = _process_storage(
            storage=operation_data_dict['storage'],
            storage_type=storage_type,
            bigmap_diffs=bigmap_diffs,
        )
        operation_data = TzktOperationData(**operation_data_dict)
        return operation_data, parse_object(storage_type, operation_data.storage)
    except IntrospectionError as e:
        raise InvalidDataError(e.args[0], storage_type, operation_data.storage) from e


# NOTE: Very smol; no need to track in performance stats
is_array_type = lru_cache(None)(is_array_type)  # type: ignore[assignment]
get_list_elt_type = lru_cache(None)(get_list_elt_type)  # type: ignore[assignment]
get_dict_value_type = lru_cache(None)(get_dict_value_type)  # type: ignore[assignment]
unwrap_union_type = lru_cache(None)(unwrap_union_type)  # type: ignore[assignment]
