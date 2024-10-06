from __future__ import annotations

import functools
import itertools
import operator

from packaging.specifiers import InvalidSpecifier as PkgInvalidSpecifier
from packaging.specifiers import Specifier, SpecifierSet
from packaging.version import Version

from dep_logic.specifiers.arbitrary import ArbitrarySpecifier
from dep_logic.specifiers.base import (
    BaseSpecifier,
    InvalidSpecifier,
    VersionSpecifier,
)
from dep_logic.specifiers.generic import GenericSpecifier
from dep_logic.specifiers.range import RangeSpecifier
from dep_logic.specifiers.special import AnySpecifier, EmptySpecifier
from dep_logic.specifiers.union import UnionSpecifier
from dep_logic.utils import is_not_suffix, version_split


def from_specifierset(spec: SpecifierSet) -> VersionSpecifier:
    """Convert from a packaging.specifiers.SpecifierSet object."""

    return functools.reduce(
        operator.and_, map(_from_pkg_specifier, spec), RangeSpecifier()
    )


def _from_pkg_specifier(spec: Specifier) -> VersionSpecifier:
    version = spec.version
    min: Version | None = None
    max: Version | None = None
    include_min = False
    include_max = False
    if (op := spec.operator) in (">", ">="):
        min = Version(version)
        include_min = spec.operator == ">="
    elif op in ("<", "<="):
        max = Version(version)
        include_max = spec.operator == "<="
    elif op == "==":
        if "*" not in version:
            min = Version(version)
            max = Version(version)
            include_min = True
            include_max = True
        else:
            version_parts = list(
                itertools.takewhile(lambda x: x != "*", version_split(version))
            )
            min = Version(".".join([*version_parts, "0"]))
            version_parts[-1] = str(int(version_parts[-1]) + 1)
            max = Version(".".join([*version_parts, "0"]))
            include_min = True
            include_max = False
    elif op == "~=":
        min = Version(version)
        version_parts = list(
            itertools.takewhile(is_not_suffix, version_split(version))
        )[:-1]
        version_parts[-1] = str(int(version_parts[-1]) + 1)
        max = Version(".".join([*version_parts, "0"]))
        include_min = True
        include_max = False
    elif op == "!=":
        if "*" not in version:
            v = Version(version)
            return UnionSpecifier(
                (
                    RangeSpecifier(max=v, include_max=False),
                    RangeSpecifier(min=v, include_min=False),
                ),
                simplified=str(spec),
            )
        else:
            version_parts = list(
                itertools.takewhile(lambda x: x != "*", version_split(version))
            )
            left = Version(".".join([*version_parts, "0"]))
            version_parts[-1] = str(int(version_parts[-1]) + 1)
            right = Version(".".join([*version_parts, "0"]))
            return UnionSpecifier(
                (
                    RangeSpecifier(max=left, include_max=False),
                    RangeSpecifier(min=right, include_min=True),
                ),
                simplified=str(spec),
            )
    elif op == "===":
        return ArbitrarySpecifier(target=version)
    else:
        raise InvalidSpecifier(f'Unsupported operator "{op}" in specifier "{spec}"')
    return RangeSpecifier(
        min=min,
        max=max,
        include_min=include_min,
        include_max=include_max,
        simplified=str(spec),
    )


def parse_version_specifier(spec: str) -> BaseSpecifier:
    """Parse a specifier string."""
    if spec == "<empty>":
        return EmptySpecifier()
    if "||" in spec:
        return functools.reduce(
            operator.or_, map(parse_version_specifier, spec.split("||"))
        )
    try:
        pkg_spec = SpecifierSet(spec)
    except PkgInvalidSpecifier as e:
        raise InvalidSpecifier(str(e)) from e
    else:
        return from_specifierset(pkg_spec)


__all__ = [
    "from_specifierset",
    "parse_version_specifier",
    "VersionSpecifier",
    "EmptySpecifier",
    "AnySpecifier",
    "RangeSpecifier",
    "UnionSpecifier",
    "BaseSpecifier",
    "GenericSpecifier",
    "ArbitrarySpecifier",
    "InvalidSpecifier",
]
