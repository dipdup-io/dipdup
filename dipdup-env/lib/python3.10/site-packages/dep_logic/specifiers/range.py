from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from dep_logic.specifiers.base import (
    BaseSpecifier,
    InvalidSpecifier,
    UnparsedVersion,
    VersionSpecifier,
)
from dep_logic.specifiers.special import EmptySpecifier
from dep_logic.utils import DATACLASS_ARGS, first_different_index, pad_zeros


@dataclass(frozen=True, unsafe_hash=True, **DATACLASS_ARGS)
class RangeSpecifier(VersionSpecifier):
    min: Version | None = None
    max: Version | None = None
    include_min: bool = False
    include_max: bool = False
    simplified: str | None = field(default=None, compare=False, hash=False)

    def __post_init__(self) -> None:
        if self.min is None and self.include_min:
            raise InvalidSpecifier("Cannot include min when min is None")
        if self.max is None and self.include_max:
            raise InvalidSpecifier("Cannot include max when max is None")

    def to_specifierset(self) -> SpecifierSet:
        return SpecifierSet(str(self))

    @property
    def num_parts(self) -> int:
        return len(self.to_specifierset())

    @cached_property
    def _simplified_form(self) -> str | None:
        if self.simplified is not None:
            return self.simplified
        if self.min is None and self.max is None:
            return ""
        elif self.min is None:
            return f"{'<=' if self.include_max else '<'}{self.max}"
        elif self.max is None:
            return f"{'>=' if self.include_min else '>'}{self.min}"
        else:
            # First, try to make a equality specifier
            if self.min == self.max:
                # include_min and include_max are always True here
                return f"=={self.min}"
            if not self.include_min or self.include_max:
                return None
            # Next, try to make a ~= specifier
            min_stable = [self.min.epoch, *self.min.release]
            max_stable = [self.max.epoch, *self.max.release]
            max_length = max(len(min_stable), len(max_stable))
            min_stable = pad_zeros(min_stable, max_length)
            max_stable = pad_zeros(max_stable, max_length)
            first_different = first_different_index(min_stable, max_stable)
            if first_different >= len(min_stable) - 1 or first_different == 0:
                # either they are all equal or the last one is different(>=2.3.1,<2.3.3)
                return None
            if max_stable[first_different] - min_stable[first_different] != 1:
                # The different part must be larger than 1
                return None
            # What's more, we need the max version to be a stable with a suffix of 0
            if (
                all(p == 0 for p in max_stable[first_different + 1 :])
                and not self.max.is_prerelease
                and len(self.min.release) == first_different + 1
            ):
                return f"~={self.min}"
            return None

    def __str__(self) -> str:
        simplified = self._simplified_form
        if simplified is not None:
            return simplified
        return f'{">=" if self.include_min else ">"}{self.min},{"<=" if self.include_max else "<"}{self.max}'

    def contains(
        self, version: UnparsedVersion, prereleases: bool | None = None
    ) -> bool:
        return self.to_specifierset().contains(version, prereleases)

    def __invert__(self) -> BaseSpecifier:
        from dep_logic.specifiers.union import UnionSpecifier

        if self.min is None and self.max is None:
            return EmptySpecifier()

        specs: list[RangeSpecifier] = []
        if self.min is not None:
            specs.append(RangeSpecifier(max=self.min, include_max=not self.include_min))
        if self.max is not None:
            specs.append(RangeSpecifier(min=self.max, include_min=not self.include_max))
        if len(specs) == 1:
            return specs[0]
        return UnionSpecifier(tuple(specs))

    def is_simple(self) -> bool:
        return self._simplified_form is not None

    def is_any(self) -> bool:
        return self.min is None and self.max is None

    def allows_lower(self, other: RangeSpecifier) -> bool:
        if other.min is None:
            return False
        if self.min is None:
            return True

        return (
            self.min < other.min
            or self.min == other.min
            and self.include_min
            and not other.include_min
        )

    def allows_higher(self, other: RangeSpecifier) -> bool:
        if other.max is None:
            return False
        if self.max is None:
            return True

        return (
            self.max > other.max
            or self.max == other.max
            and self.include_max
            and not other.include_max
        )

    def is_strictly_lower(self, other: RangeSpecifier) -> bool:
        """Return True if this range is lower than the other range
        and they have no overlap.
        """
        if self.max is None or other.min is None:
            return False

        return (
            self.max < other.min
            or self.max == other.min
            and False in (self.include_max, other.include_min)
        )

    def is_adjacent_to(self, other: RangeSpecifier) -> bool:
        if self.max is None or other.min is None:
            return False
        return (
            self.max == other.min
            and [self.include_max, other.include_min].count(True) == 1
        )

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, RangeSpecifier):
            return NotImplemented
        return self.allows_lower(other)

    def is_superset(self, other: RangeSpecifier) -> bool:
        min_lower = (
            self.min is None
            or other.min is not None
            and (
                self.min < other.min
                or self.min == other.min
                and not (not self.include_min and other.include_min)
            )
        )
        max_higher = (
            self.max is None
            or other.max is not None
            and (
                self.max > other.max
                or self.max == other.max
                and not (not self.include_max and other.include_max)
            )
        )
        return min_lower and max_higher

    def is_subset(self, other: RangeSpecifier) -> bool:
        return other.is_superset(self)

    def can_combine(self, other: RangeSpecifier) -> bool:
        """Return True if the two ranges can be combined into one range."""
        if self.allows_lower(other):
            return not self.is_strictly_lower(other) or self.is_adjacent_to(other)
        else:
            return not other.is_strictly_lower(self) or other.is_adjacent_to(self)

    def __and__(self, other: Any) -> RangeSpecifier | EmptySpecifier:
        if not isinstance(other, RangeSpecifier):
            return NotImplemented
        if self.is_superset(other):
            return other

        if other.is_superset(self):
            return self

        if self.allows_lower(other):
            if self.is_strictly_lower(other):
                return EmptySpecifier()
            intersect_min = other.min
            intersect_include_min = other.include_min
        else:
            if other.is_strictly_lower(self):
                return EmptySpecifier()
            intersect_min = self.min
            intersect_include_min = self.include_min

        if self.allows_higher(other):
            intersect_max = other.max
            intersect_include_max = other.include_max
        else:
            intersect_max = self.max
            intersect_include_max = self.include_max

        return type(self)(
            min=intersect_min,
            max=intersect_max,
            include_min=intersect_include_min,
            include_max=intersect_include_max,
        )

    def __or__(self, other: Any) -> VersionSpecifier:
        from dep_logic.specifiers.union import UnionSpecifier

        if not isinstance(other, RangeSpecifier):
            return NotImplemented

        if self.is_superset(other):
            return self
        if other.is_superset(self):
            return other

        if self.allows_lower(other):
            if self.is_strictly_lower(other) and not self.is_adjacent_to(other):
                return UnionSpecifier((self, other))
            union_min = self.min
            union_include_min = self.include_min
        else:
            if other.is_strictly_lower(self) and not other.is_adjacent_to(self):
                return UnionSpecifier((other, self))
            union_min = other.min
            union_include_min = other.include_min

        if self.allows_higher(other):
            union_max = self.max
            union_include_max = self.include_max
        else:
            union_max = other.max
            union_include_max = other.include_max

        return type(self)(
            min=union_min,
            max=union_max,
            include_min=union_include_min,
            include_max=union_include_max,
        )
