from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from packaging.specifiers import SpecifierSet

from dep_logic.specifiers.base import BaseSpecifier, UnparsedVersion, VersionSpecifier
from dep_logic.specifiers.special import EmptySpecifier
from dep_logic.utils import DATACLASS_ARGS


@dataclass(frozen=True, unsafe_hash=True, **DATACLASS_ARGS)
class ArbitrarySpecifier(VersionSpecifier):
    """`===<version_string>` specifier."""

    target: str

    def to_specifierset(self) -> SpecifierSet:
        return SpecifierSet(f"==={self.target}")

    def __str__(self) -> str:
        return f"==={self.target}"

    def contains(
        self, version: UnparsedVersion, prereleases: bool | None = None
    ) -> bool:
        return str(version) == self.target

    @property
    def num_parts(self) -> int:
        return 1

    def is_simple(self) -> bool:
        return True

    def __invert__(self) -> BaseSpecifier:
        raise ValueError("Cannot invert an ArbitrarySpecifier")

    def __and__(self, other: Any) -> BaseSpecifier:
        if not isinstance(other, VersionSpecifier):
            return NotImplemented
        if other.is_empty():
            return other
        try:
            if other.is_any() or self.target in other:
                return self
            return EmptySpecifier()
        except ValueError:
            raise ValueError(
                f"Unsupported intersection of '{self}' and '{other}'"
            ) from None

    __rand__ = __and__

    def __or__(self, other: Any) -> BaseSpecifier:
        if not isinstance(other, VersionSpecifier):
            return NotImplemented
        if other.is_empty():
            return self
        try:
            if other.is_any() or self.target in other:
                return other
        except ValueError:
            pass
        raise ValueError(f"Unsupported union of '{self}' and '{other}'") from None

    __ror__ = __or__
