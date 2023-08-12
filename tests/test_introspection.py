from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import pytest
from pydantic import BaseModel

from dipdup.indexes.tezos_tzkt_operations.parser import IntrospectionError
from dipdup.indexes.tezos_tzkt_operations.parser import extract_root_outer_type
from dipdup.indexes.tezos_tzkt_operations.parser import get_dict_value_type
from dipdup.indexes.tezos_tzkt_operations.parser import get_list_elt_type
from dipdup.indexes.tezos_tzkt_operations.parser import is_array_type
from dipdup.indexes.tezos_tzkt_operations.parser import unwrap_union_type

NoneType = type(None)


def test_list_simple_args() -> None:
    assert get_list_elt_type(List[str]) == str
    assert get_list_elt_type(List[int]) == int
    assert get_list_elt_type(List[bool]) == bool
    assert get_list_elt_type(List[Optional[str]]) == Optional[str]
    assert get_list_elt_type(List[Union[str, int]]) == Union[str, int]
    assert get_list_elt_type(List[Tuple[str]]) == Tuple[str]
    assert get_list_elt_type(List[List[str]]) == List[str]
    assert get_list_elt_type(List[Dict[str, str]]) == Dict[str, str]


def test_list_complex_arg() -> None:
    class Class:
        ...

    assert get_list_elt_type(List[Class]) == Class
    assert get_list_elt_type(List[Optional[Class]]) == Optional[Class]
    assert get_list_elt_type(List[Union[Class, int]]) == Union[Class, int]
    assert get_list_elt_type(List[Tuple[Class]]) == Tuple[Class]
    assert get_list_elt_type(List[List[Class]]) == List[Class]
    assert get_list_elt_type(List[Dict[str, Class]]) == Dict[str, Class]


def test_pydantic_list_arg() -> None:
    class ListOfMapsStorage(BaseModel):
        __root__: List[Union[int, Dict[str, str]]]

    class SomethingElse(BaseModel):
        __root__: Dict[str, str]

    class OptionalList(BaseModel):
        __root__: Optional[List[str]]

    assert get_list_elt_type(ListOfMapsStorage) == Union[int, Dict[str, str]]

    with pytest.raises(IntrospectionError):
        get_list_elt_type(OptionalList)

    with pytest.raises(IntrospectionError):
        get_list_elt_type(SomethingElse)


def test_dict_simple_args() -> None:
    assert get_dict_value_type(Dict[str, str]) == str
    assert get_dict_value_type(Dict[str, int]) == int
    assert get_dict_value_type(Dict[str, bool]) == bool
    assert get_dict_value_type(Dict[str, Optional[str]]) == Optional[str]
    assert get_dict_value_type(Dict[str, Union[str, int]]) == Union[str, int]
    assert get_dict_value_type(Dict[str, Tuple[str]]) == Tuple[str]
    assert get_dict_value_type(Dict[str, List[str]]) == List[str]
    assert get_dict_value_type(Dict[str, Dict[str, str]]) == Dict[str, str]


def test_dict_complex_arg() -> None:
    class Class:
        ...

    assert get_dict_value_type(Dict[str, Class]) == Class
    assert get_dict_value_type(Dict[str, Optional[Class]]) == Optional[Class]
    assert get_dict_value_type(Dict[str, Union[Class, int]]) == Union[Class, int]
    assert get_dict_value_type(Dict[str, Tuple[Class]]) == Tuple[Class]
    assert get_dict_value_type(Dict[str, List[Class]]) == List[Class]
    assert get_dict_value_type(Dict[str, Dict[str, Class]]) == Dict[str, Class]


def test_pydantic_dict_arg() -> None:
    class DictOfMapsStorage(BaseModel):
        __root__: Dict[str, Union[int, Dict[str, str]]]

    class SomethingElse(BaseModel):
        __root__: List[str]

    class OptionalDict(BaseModel):
        __root__: Optional[Dict[str, str]]

    assert get_dict_value_type(DictOfMapsStorage) == Union[int, Dict[str, str]]
    with pytest.raises(IntrospectionError):
        get_dict_value_type(OptionalDict)

    with pytest.raises(IntrospectionError):
        get_dict_value_type(SomethingElse)


def test_pydantic_object_key() -> None:
    class Storage(BaseModel):
        plain_str: str
        list_str: List[str]
        dict_of_lists: Dict[str, List[str]]
        optional_str: Optional[str]
        union_arg: Union[str, int]

    assert get_dict_value_type(Storage, 'plain_str') == str
    assert get_dict_value_type(Storage, 'list_str') == List[str]
    assert get_dict_value_type(Storage, 'dict_of_lists') == Dict[str, List[str]]
    assert get_dict_value_type(Storage, 'optional_str') == Optional[str]
    assert get_dict_value_type(Storage, 'union_arg') == Union[str, int]


def test_is_array() -> None:
    class ListOfMapsStorage(BaseModel):
        __root__: List[Union[int, Dict[str, str]]]

    class OptionalList(BaseModel):
        __root__: Optional[List[str]]

    assert is_array_type(List[str]) is True
    assert is_array_type(ListOfMapsStorage) is True
    assert is_array_type(OptionalList) is False


def test_simple_union_unwrap() -> None:
    assert unwrap_union_type(Optional[str]) == (True, (str, NoneType))  # type: ignore[arg-type,comparison-overlap]
    assert unwrap_union_type(Union[int, str]) == (True, (int, str))  # type: ignore[arg-type]


def test_pydantic_optional_unwrap() -> None:
    class UnionIntStr(BaseModel):
        __root__: Union[int, str]

    class OptionalStr(BaseModel):
        __root__: Optional[str]

    assert unwrap_union_type(OptionalStr) == (True, (str, NoneType))  # type: ignore[comparison-overlap]
    assert unwrap_union_type(UnionIntStr) == (True, (int, str))


def test_root_type_extraction() -> None:
    class OptionalStr(BaseModel):
        __root__: Optional[str]

    class ListOfMapsStorage(BaseModel):
        __root__: List[Union[int, Dict[str, str]]]

    assert extract_root_outer_type(OptionalStr) == Optional[str]
    # FIXME: left operand type: "Type[BaseModel]", right operand type: "Type[List[Any]]"
    assert extract_root_outer_type(ListOfMapsStorage) == List[Union[int, Dict[str, str]]]  # type: ignore[comparison-overlap]
