from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
from unittest import TestCase

from pydantic import BaseModel

from dipdup.datasources.tzkt.models import IntrospectionError
from dipdup.datasources.tzkt.models import extract_root_outer_type
from dipdup.datasources.tzkt.models import get_dict_value_type
from dipdup.datasources.tzkt.models import get_list_elt_type
from dipdup.datasources.tzkt.models import is_array_type
from dipdup.datasources.tzkt.models import unwrap_union_type

NoneType = type(None)


class IntrospectionTest(TestCase):
    def test_list_simple_args(self) -> None:
        self.assertEqual(str, get_list_elt_type(List[str]))
        self.assertEqual(int, get_list_elt_type(List[int]))
        self.assertEqual(bool, get_list_elt_type(List[bool]))
        self.assertEqual(Optional[str], get_list_elt_type(List[Optional[str]]))
        self.assertEqual(Union[str, int], get_list_elt_type(List[Union[str, int]]))
        self.assertEqual(Tuple[str], get_list_elt_type(List[Tuple[str]]))
        self.assertEqual(List[str], get_list_elt_type(List[List[str]]))
        self.assertEqual(Dict[str, str], get_list_elt_type(List[Dict[str, str]]))

    def test_list_complex_arg(self) -> None:
        class Class:
            ...

        self.assertEqual(Class, get_list_elt_type(List[Class]))
        self.assertEqual(Optional[Class], get_list_elt_type(List[Optional[Class]]))
        self.assertEqual(Union[Class, int], get_list_elt_type(List[Union[Class, int]]))
        self.assertEqual(Tuple[Class], get_list_elt_type(List[Tuple[Class]]))
        self.assertEqual(List[Class], get_list_elt_type(List[List[Class]]))
        self.assertEqual(Dict[str, Class], get_list_elt_type(List[Dict[str, Class]]))

    def test_pydantic_list_arg(self) -> None:
        class ListOfMapsStorage(BaseModel):
            __root__: List[Union[int, Dict[str, str]]]

        class SomethingElse(BaseModel):
            __root__: Dict[str, str]

        class OptionalList(BaseModel):
            __root__: Optional[List[str]]

        self.assertEqual(Union[int, Dict[str, str]], get_list_elt_type(ListOfMapsStorage))

        with self.assertRaises(IntrospectionError):
            get_list_elt_type(OptionalList)

        with self.assertRaises(IntrospectionError):
            get_list_elt_type(SomethingElse)

    def test_dict_simple_args(self) -> None:
        self.assertEqual(str, get_dict_value_type(Dict[str, str]))
        self.assertEqual(int, get_dict_value_type(Dict[str, int]))
        self.assertEqual(bool, get_dict_value_type(Dict[str, bool]))
        self.assertEqual(Optional[str], get_dict_value_type(Dict[str, Optional[str]]))
        self.assertEqual(Union[str, int], get_dict_value_type(Dict[str, Union[str, int]]))
        self.assertEqual(Tuple[str], get_dict_value_type(Dict[str, Tuple[str]]))
        self.assertEqual(List[str], get_dict_value_type(Dict[str, List[str]]))
        self.assertEqual(Dict[str, str], get_dict_value_type(Dict[str, Dict[str, str]]))

    def test_dict_complex_arg(self) -> None:
        class Class:
            ...

        self.assertEqual(Class, get_dict_value_type(Dict[str, Class]))
        self.assertEqual(Optional[Class], get_dict_value_type(Dict[str, Optional[Class]]))
        self.assertEqual(Union[Class, int], get_dict_value_type(Dict[str, Union[Class, int]]))
        self.assertEqual(Tuple[Class], get_dict_value_type(Dict[str, Tuple[Class]]))
        self.assertEqual(List[Class], get_dict_value_type(Dict[str, List[Class]]))
        self.assertEqual(Dict[str, Class], get_dict_value_type(Dict[str, Dict[str, Class]]))

    def test_pydantic_dict_arg(self) -> None:
        class DictOfMapsStorage(BaseModel):
            __root__: Dict[str, Union[int, Dict[str, str]]]

        class SomethingElse(BaseModel):
            __root__: List[str]

        class OptionalDict(BaseModel):
            __root__: Optional[Dict[str, str]]

        self.assertEqual(Union[int, Dict[str, str]], get_dict_value_type(DictOfMapsStorage))
        with self.assertRaises(IntrospectionError):
            get_dict_value_type(OptionalDict)

        with self.assertRaises(IntrospectionError):
            get_dict_value_type(SomethingElse)

    def test_pydantic_object_key(self) -> None:
        class Storage(BaseModel):
            plain_str: str
            list_str: List[str]
            dict_of_lists: Dict[str, List[str]]
            optional_str: Optional[str]
            union_arg: Union[str, int]

        self.assertEqual(str, get_dict_value_type(Storage, 'plain_str'))
        self.assertEqual(List[str], get_dict_value_type(Storage, 'list_str'))
        self.assertEqual(Dict[str, List[str]], get_dict_value_type(Storage, 'dict_of_lists'))
        self.assertEqual(Optional[str], get_dict_value_type(Storage, 'optional_str'))
        self.assertEqual(Union[str, int], get_dict_value_type(Storage, 'union_arg'))

    def test_is_array(self) -> None:
        class ListOfMapsStorage(BaseModel):
            __root__: List[Union[int, Dict[str, str]]]

        class SomethingElse(BaseModel):
            __root__: Dict[str, str]

        class OptionalList(BaseModel):
            __root__: Optional[List[str]]

        self.assertTrue(is_array_type(List[str]))
        self.assertTrue(is_array_type(ListOfMapsStorage))
        self.assertFalse(is_array_type(OptionalList))

    def test_simple_union_unwrap(self) -> None:
        self.assertEqual((True, (str, NoneType)), unwrap_union_type(Optional[str]))
        self.assertEqual((True, (int, str)), unwrap_union_type(Union[int, str]))

    def test_pydantic_optional_unwrap(self) -> None:
        class UnionIntStr(BaseModel):
            __root__: Union[int, str]

        class OptionalStr(BaseModel):
            __root__: Optional[str]

        self.assertEqual((True, (str, NoneType)), unwrap_union_type(OptionalStr))
        self.assertEqual((True, (int, str)), unwrap_union_type(UnionIntStr))

    def test_root_type_extraction(self) -> None:
        class OptionalStr(BaseModel):
            __root__: Optional[str]

        class ListOfMapsStorage(BaseModel):
            __root__: List[Union[int, Dict[str, str]]]

        self.assertEqual(Optional[str], extract_root_outer_type(OptionalStr))
        self.assertEqual(List[Union[int, Dict[str, str]]], extract_root_outer_type(ListOfMapsStorage))
