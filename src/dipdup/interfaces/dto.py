from typing import List, Optional

from humps import camelize, pascalize  # type: ignore
from pydantic import Field
from pydantic.dataclasses import dataclass

from dipdup.interfaces.const import InterfaceCodegenConst


@dataclass
class ParameterDTO:
    name: str
    type: Optional[str] = InterfaceCodegenConst.EMPTY_STRING

    def __str__(self) -> str:
        if self.type:
            return f'{self.name}: {self.type}'

        return f'{self.name}'


@dataclass
class MethodDefinitionDTO:
    name: str
    parameters: List[ParameterDTO]
    decorators: Optional[List[str]] = Field(default_factory=list)
    return_type: str = InterfaceCodegenConst.DEFAULT_RETURN_TYPE

    def __str__(self) -> str:
        return f'{InterfaceCodegenConst.METHOD_DEFINITION} {self.method_name}({self.get_parameters()}) -> {self.return_type}:'

    def get_parameters(self) -> str:
        return InterfaceCodegenConst.COMMA_DELIMITER.join(map(str, self.parameters))

    @property
    def method_name(self) -> str:
        return f'{camelize(self.name)}'


@dataclass
class EntrypointDTO:
    definition: MethodDefinitionDTO
    code: List[str] = Field(default_factory=list)


@dataclass
class ImportDTO:
    module: str
    class_name: str


@dataclass
class ClassDefinitionDTO:
    name: str
    parents: Optional[List[str]] = Field(default_factory=list)

    def __str__(self) -> str:
        return f'{InterfaceCodegenConst.CLASS_DEFINITION} {self.class_name}{self.get_parents()}:'

    @property
    def class_name(self) -> str:
        return f'{pascalize(self.name)}{InterfaceCodegenConst.INTERFACE_CLASS_POSTFIX}'

    def get_parents(self):
        if self.parents:
            return f'({InterfaceCodegenConst.COMMA_DELIMITER.join(self.parents)})'


@dataclass
class InterfaceDTO:
    definition: ClassDefinitionDTO
    methods: List[EntrypointDTO] = Field(default_factory=list)


@dataclass
class TemplateDTO:
    interface: InterfaceDTO
    imports: List[ImportDTO] = Field(default_factory=list)
