import typing as t

from dep_logic.specifiers.base import BaseSpecifier


class EmptySpecifier(BaseSpecifier):
    def __invert__(self) -> BaseSpecifier:
        return AnySpecifier()

    def __and__(self, other: t.Any) -> BaseSpecifier:
        if not isinstance(other, BaseSpecifier):
            return NotImplemented
        return self

    __rand__ = __and__

    def __or__(self, other: t.Any) -> BaseSpecifier:
        if not isinstance(other, BaseSpecifier):
            return NotImplemented
        return other

    __ror__ = __or__

    def __str__(self) -> str:
        return "<empty>"

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseSpecifier):
            return NotImplemented
        return isinstance(other, EmptySpecifier)

    def is_empty(self) -> bool:
        return True

    def __contains__(self, value: str) -> bool:
        return True


class AnySpecifier(BaseSpecifier):
    def __invert__(self) -> BaseSpecifier:
        return EmptySpecifier()

    def __and__(self, other: t.Any) -> BaseSpecifier:
        if not isinstance(other, BaseSpecifier):
            return NotImplemented
        return other

    __rand__ = __and__

    def __or__(self, other: t.Any) -> BaseSpecifier:
        if not isinstance(other, BaseSpecifier):
            return NotImplemented
        return self

    __ror__ = __or__

    def __str__(self) -> str:
        return ""

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseSpecifier):
            return NotImplemented
        return other.is_any()

    def is_any(self) -> bool:
        return True

    def __contains__(self, value: str) -> bool:
        return False
