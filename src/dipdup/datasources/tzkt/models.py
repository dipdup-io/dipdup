import typing
from contextlib import suppress
from functools import lru_cache
from itertools import groupby
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type
from typing import Union

from pydantic import Extra
from pydantic.error_wrappers import ValidationError
from typing_extensions import get_args
from typing_extensions import get_origin

from dipdup.exceptions import InvalidDataError
from dipdup.models import OperationData
from dipdup.models import StorageType

IntrospectionError = (KeyError, IndexError, AttributeError)


def extract_root_outer_type(storage_type: Type) -> Type:
    """Extract Pydantic __root__ type"""
    root_field = storage_type.__fields__['__root__']
    if root_field.allow_none:
        return typing.Optional[root_field.type_]  # type: ignore
    else:
        return root_field.outer_type_


@lru_cache(None)
def is_array_type(storage_type: Type) -> bool:
    """TzKT can return bigmaps as objects or as arrays of key-value objects. Guess it from storage type."""
    # NOTE: List[...]
    if get_origin(storage_type) == list:
        return True

    # NOTE: Pydantic model with __root__ field subclassing List
    with suppress(*IntrospectionError):
        root_type = extract_root_outer_type(storage_type)
        return is_array_type(root_type)  # type: ignore

    # NOTE: Something else
    return False


@lru_cache(None)
def get_list_elt_type(list_type: Type[Any]) -> Type[Any]:
    """Extract list item type from list type"""
    # NOTE: regular list
    if get_origin(list_type) == list:
        return get_args(list_type)[0]

    # NOTE: Pydantic model with __root__ field subclassing List
    root_type = extract_root_outer_type(list_type)
    return get_list_elt_type(root_type)  # type: ignore


@lru_cache(None)
def get_dict_value_type(dict_type: Type[Any], key: Optional[str] = None) -> Type[Any]:
    """Extract dict value types from field type"""
    # NOTE: Regular dict
    if get_origin(dict_type) == dict:
        return get_args(dict_type)[1]

    # NOTE: Pydantic model with __root__ field subclassing Dict
    with suppress(*IntrospectionError):
        root_type = extract_root_outer_type(dict_type)
        return get_dict_value_type(root_type, key)  # type: ignore

    if key is None:
        raise KeyError('Field name or alias is required for object introspection')

    # NOTE: Pydantic model, find corresponding field and return it's type
    fields = dict_type.__fields__
    for field in fields.values():
        if key in (field.name, field.alias):
            # NOTE: Pydantic does not preserve outer_type_ for Optional
            if field.allow_none:
                return typing.Optional[field.type_]  # type: ignore
            else:
                return field.outer_type_

    # NOTE: Either we try the wrong Union path or model was modifier by user
    raise KeyError(f'Field `{key}` not found in {dict_type}')


@lru_cache(None)
def unwrap_union_type(union_type: Type) -> Tuple[bool, Tuple[Type, ...]]:
    """Check if the type is either optional or union and return arg types if so"""
    if get_origin(union_type) == Union:
        return True, get_args(union_type)

    with suppress(*IntrospectionError):
        root_type = extract_root_outer_type(union_type)
        return unwrap_union_type(root_type)  # type: ignore

    return False, ()


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


def _process_storage(storage: Any, storage_type: Type[Any], bigmap_diffs: Dict[int, Iterable[Dict[str, Any]]]) -> Any:
    """Replace bigmap pointers with actual data from diffs"""
    # Check if Union or Optional (== Union[Any, NoneType])
    is_union, arg_types = unwrap_union_type(storage_type)  # type: ignore
    if is_union:
        # NOTE: We have no way but trying every possible branch until first success
        for arg_type in arg_types:
            with suppress(*IntrospectionError):
                return _process_storage(storage, arg_type, bigmap_diffs)

    # NOTE: Bigmap pointer, apply diffs
    if isinstance(storage, int) and type(storage) != storage_type:
        is_array = is_array_type(storage_type)  # type: ignore
        storage = _apply_bigmap_diffs(storage, bigmap_diffs, is_array)

    # NOTE: List, process recursively
    elif isinstance(storage, list):
        elt_type = get_list_elt_type(storage_type)  # type: ignore
        for i, _ in enumerate(storage):
            storage[i] = _process_storage(storage[i], elt_type, bigmap_diffs)

    # NOTE: Dict, process recursively
    elif isinstance(storage, dict):
        # NOTE: Ignore missing fields along with extra ones
        ignore = getattr(getattr(storage_type, 'Config', None), 'extra', None) == Extra.ignore

        for key, value in storage.items():
            try:
                value_type = get_dict_value_type(storage_type, key)  # type: ignore
                storage[key] = _process_storage(value, value_type, bigmap_diffs)
            except IntrospectionError:
                if not ignore:
                    raise

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
