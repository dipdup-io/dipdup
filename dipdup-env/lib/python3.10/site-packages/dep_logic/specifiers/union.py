from __future__ import annotations

import itertools
import typing as t
from dataclasses import dataclass, field
from functools import cached_property

from packaging.specifiers import SpecifierSet

from dep_logic.specifiers.base import BaseSpecifier, UnparsedVersion, VersionSpecifier
from dep_logic.specifiers.range import RangeSpecifier
from dep_logic.specifiers.special import EmptySpecifier
from dep_logic.utils import DATACLASS_ARGS, first_different_index, pad_zeros


@dataclass(frozen=True, unsafe_hash=True, **DATACLASS_ARGS)
class UnionSpecifier(VersionSpecifier):
    ranges: tuple[RangeSpecifier, ...]
    simplified: str | None = field(default=None, compare=False, hash=False)

    def to_specifierset(self) -> SpecifierSet:
        if (simplified := self._simplified_form) is None:
            raise ValueError("Cannot convert UnionSpecifier to SpecifierSet")
        return SpecifierSet(simplified)

    @property
    def num_parts(self) -> int:
        return sum(range.num_parts for range in self.ranges)

    @cached_property
    def _simplified_form(self) -> str | None:
        if self.simplified is not None:
            return self.simplified
        # try to get a not-equals form(!=) if possible
        left, right, *rest = self.ranges
        if rest:
            return None
        if (
            left.min is None
            and right.max is None
            and left.max == right.min
            and left.max is not None
        ):
            # (-inf, version) | (version, inf) => != version
            return f"!={left.max}"

        if (
            left.min is None
            and right.max is None
            and not left.include_max
            and right.include_min
            and left.max is not None
            and right.min is not None
        ):
            # (-inf, X.Y.0) | [X.Y+1.0, inf) => != X.Y.*
            if left.max.is_prerelease or right.min.is_prerelease:
                return None
            left_stable = [left.max.epoch, *left.max.release]
            right_stable = [right.min.epoch, *right.min.release]
            max_length = max(len(left_stable), len(right_stable))
            left_stable = pad_zeros(left_stable, max_length)
            right_stable = pad_zeros(right_stable, max_length)
            first_different = first_different_index(left_stable, right_stable)
            if (
                first_different > 0
                and right_stable[first_different] - left_stable[first_different] == 1
                and set(
                    left_stable[first_different + 1 :]
                    + right_stable[first_different + 1 :]
                )
                == {0}
            ):
                epoch = "" if left.max.epoch == 0 else f"{left.max.epoch}!"
                version = ".".join(map(str, left.max.release[:first_different])) + ".*"
                return f"!={epoch}{version}"

        return None

    def __str__(self) -> str:
        if self._simplified_form is not None:
            return self._simplified_form
        return "||".join(map(str, self.ranges))

    @staticmethod
    def _from_ranges(ranges: t.Sequence[RangeSpecifier]) -> BaseSpecifier:
        if (ranges_number := len(ranges)) == 0:
            return EmptySpecifier()
        elif ranges_number == 1:
            return ranges[0]
        else:
            return UnionSpecifier(tuple(ranges))

    def is_simple(self) -> bool:
        return self._simplified_form is not None

    def contains(
        self, version: UnparsedVersion, prereleases: bool | None = None
    ) -> bool:
        return any(
            specifier.contains(version, prereleases) for specifier in self.ranges
        )

    def __invert__(self) -> BaseSpecifier:
        to_union: list[RangeSpecifier] = []
        if (first := self.ranges[0]).min is not None:
            to_union.append(
                RangeSpecifier(max=first.min, include_max=not first.include_min)
            )
        for a, b in zip(self.ranges, self.ranges[1:]):
            to_union.append(
                RangeSpecifier(
                    min=a.max,
                    include_min=not a.include_max,
                    max=b.min,
                    include_max=not b.include_min,
                )
            )
        if (last := self.ranges[-1]).max is not None:
            to_union.append(
                RangeSpecifier(min=last.max, include_min=not last.include_max)
            )
        return self._from_ranges(to_union)

    def __and__(self, other: t.Any) -> BaseSpecifier:
        if isinstance(other, RangeSpecifier):
            if other.is_any():
                return self
            to_intersect: list[RangeSpecifier] = [other]
        elif isinstance(other, UnionSpecifier):
            to_intersect = list(other.ranges)
        else:
            return NotImplemented
        # Expand the ranges to be intersected, and discard the empty ones
        #   (a | b) & (c | d) = (a & c) | (a & d) | (b & c) | (b & d)
        # Since each subrange doesn't overlap with each other and intersection
        # only makes it smaller, so the result is also guaranteed to be a set
        # of non-overlapping ranges, just build a new union from them.
        new_ranges = [
            range
            for (a, b) in itertools.product(self.ranges, to_intersect)
            if not isinstance(range := a & b, EmptySpecifier)
        ]
        return self._from_ranges(new_ranges)

    __rand__ = __and__

    def __or__(self, other: t.Any) -> BaseSpecifier:
        if isinstance(other, RangeSpecifier):
            if other.is_any():
                return other
            new_ranges: list[RangeSpecifier] = []
            ranges = iter(self.ranges)
            for range in ranges:
                if range.can_combine(other):
                    other = t.cast(RangeSpecifier, other | range)
                elif other.allows_lower(range):
                    # all following ranges are higher than the input, quit the loop
                    # and copy the rest ranges.
                    new_ranges.extend([other, range, *ranges])
                    break
                else:
                    # range is strictly lower than other, nothing to do here
                    new_ranges.append(range)
            else:
                # we have consumed all ranges or no range is merged,
                # just append to the last.
                new_ranges.append(other)
            return self._from_ranges(new_ranges)
        elif isinstance(other, UnionSpecifier):
            result = self
            for range in other.ranges:
                result = result | range
            return result
        else:
            return NotImplemented

    __ror__ = __or__
