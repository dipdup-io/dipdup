from __future__ import annotations

import abc
import typing as t

from packaging.specifiers import SpecifierSet
from packaging.version import Version

UnparsedVersion = t.Union[Version, str]


class InvalidSpecifier(ValueError):
    pass


class BaseSpecifier(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __str__(self) -> str:
        """
        Returns the str representation of this Specifier-like object. This
        should be representative of the Specifier itself.
        """

    @abc.abstractmethod
    def __and__(self, other: t.Any) -> BaseSpecifier:
        raise NotImplementedError

    @abc.abstractmethod
    def __or__(self, other: t.Any) -> BaseSpecifier:
        raise NotImplementedError

    @abc.abstractmethod
    def __invert__(self) -> BaseSpecifier:
        raise NotImplementedError

    def is_simple(self) -> bool:
        return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self}>"

    def is_empty(self) -> bool:
        return False

    def is_any(self) -> bool:
        return False

    @abc.abstractmethod
    def __contains__(self, value: str) -> bool:
        raise NotImplementedError


class VersionSpecifier(BaseSpecifier):
    @abc.abstractmethod
    def contains(
        self, version: UnparsedVersion, prereleases: bool | None = None
    ) -> bool:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def num_parts(self) -> int:
        raise NotImplementedError

    def __contains__(self, version: UnparsedVersion) -> bool:
        return self.contains(version)

    @abc.abstractmethod
    def to_specifierset(self) -> SpecifierSet:
        """Convert to a packaging.specifiers.SpecifierSet object."""
        raise NotImplementedError
