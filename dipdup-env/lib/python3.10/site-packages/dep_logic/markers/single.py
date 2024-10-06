from __future__ import annotations

import functools
import typing as t
from dataclasses import dataclass, field, replace

from packaging.markers import Marker as _Marker

from dep_logic.markers.any import AnyMarker
from dep_logic.markers.base import BaseMarker
from dep_logic.markers.empty import EmptyMarker
from dep_logic.specifiers import BaseSpecifier
from dep_logic.specifiers.base import VersionSpecifier
from dep_logic.specifiers.generic import GenericSpecifier
from dep_logic.utils import DATACLASS_ARGS, OrderedSet, get_reflect_op

if t.TYPE_CHECKING:
    from dep_logic.markers.multi import MultiMarker
    from dep_logic.markers.union import MarkerUnion

PYTHON_VERSION_MARKERS = {"python_version", "python_full_version"}


class SingleMarker(BaseMarker):
    name: str
    _VERSION_LIKE_MARKER_NAME: t.ClassVar[set[str]] = {
        "python_version",
        "python_full_version",
        "platform_release",
    }

    def without_extras(self) -> BaseMarker:
        return self.exclude("extra")

    def exclude(self, marker_name: str) -> BaseMarker:
        if self.name == marker_name:
            return AnyMarker()

        return self

    def only(self, *marker_names: str) -> BaseMarker:
        if self.name not in marker_names:
            return AnyMarker()

        return self

    def evaluate(self, environment: dict[str, str] | None = None) -> bool:
        pkg_marker = _Marker(str(self))
        if self.name != "extra" or not environment or "extra" not in environment:
            return pkg_marker.evaluate(environment)
        extras = [extra] if isinstance(extra := environment["extra"], str) else extra
        assert isinstance(self, MarkerExpression)
        is_negated = self.op in ("not in", "!=")
        if is_negated:
            return all(pkg_marker.evaluate({"extra": extra}) for extra in extras)
        return any(pkg_marker.evaluate({"extra": extra}) for extra in extras)


@dataclass(unsafe_hash=True, **DATACLASS_ARGS)
class MarkerExpression(SingleMarker):
    name: str
    op: str
    value: str
    reversed: bool = field(default=False, compare=False, hash=False)
    _specifier: BaseSpecifier | None = field(default=None, compare=False, hash=False)

    @property
    def specifier(self) -> BaseSpecifier:
        if self._specifier is None:
            self._specifier = self._get_specifier()
        return self._specifier

    @classmethod
    def from_specifier(cls, name: str, specifier: BaseSpecifier) -> BaseMarker | None:
        if specifier.is_any():
            return AnyMarker()
        if specifier.is_empty():
            return EmptyMarker()
        if isinstance(specifier, VersionSpecifier):
            if not specifier.is_simple():
                return None
            pkg_spec = next(iter(specifier.to_specifierset()))
            pkg_version = pkg_spec.version
            if (
                dot_num := pkg_version.count(".")
            ) < 2 and name == "python_full_version":
                for _ in range(2 - dot_num):
                    pkg_version += ".0"
            return MarkerExpression(
                name, pkg_spec.operator, pkg_version, _specifier=specifier
            )
        assert isinstance(specifier, GenericSpecifier)
        return MarkerExpression(
            name, specifier.op, specifier.value, _specifier=specifier
        )

    def _get_specifier(self) -> BaseSpecifier:
        from dep_logic.specifiers import parse_version_specifier

        if self.name not in self._VERSION_LIKE_MARKER_NAME:
            return GenericSpecifier(self.op, self.value)
        if self.op in ("in", "not in"):
            versions: list[str] = []
            op, glue = ("==", "||") if self.op == "in" else ("!=", ",")
            for part in self.value.split(","):
                splitted = part.strip().split(".")
                if part_num := len(splitted) < 3:
                    if self.name == "python_version":
                        splitted.append("*")
                    else:
                        splitted.extend(["0"] * (3 - part_num))

                versions.append(op + ".".join(splitted))
            return parse_version_specifier(glue.join(versions))
        return parse_version_specifier(f"{self.op}{self.value}")

    def __str__(self) -> str:
        if self.reversed:
            return f'"{self.value}" {get_reflect_op(self.op)} {self.name}'
        return f'{self.name} {self.op} "{self.value}"'

    def __and__(self, other: t.Any) -> BaseMarker:
        from dep_logic.markers.multi import MultiMarker

        if not isinstance(other, MarkerExpression):
            return NotImplemented
        merged = _merge_single_markers(self, other, MultiMarker)
        if merged is not None:
            return merged

        return MultiMarker(self, other)

    def __or__(self, other: t.Any) -> BaseMarker:
        from dep_logic.markers.union import MarkerUnion

        if not isinstance(other, MarkerExpression):
            return NotImplemented
        merged = _merge_single_markers(self, other, MarkerUnion)
        if merged is not None:
            return merged

        return MarkerUnion(self, other)


@dataclass(frozen=True, unsafe_hash=True, **DATACLASS_ARGS)
class EqualityMarkerUnion(SingleMarker):
    name: str
    values: OrderedSet[str]

    def __str__(self) -> str:
        return " or ".join(f'{self.name} == "{value}"' for value in self.values)

    def replace(self, values: OrderedSet[str]) -> BaseMarker:
        if not values:
            return EmptyMarker()
        if len(values) == 1:
            return MarkerExpression(self.name, "==", values.peek())
        return replace(self, values=values)

    @property
    def complexity(self) -> tuple[int, ...]:
        return len(self.values), 1

    def __and__(self, other: t.Any) -> BaseMarker:
        from dep_logic.markers.multi import MultiMarker

        if not isinstance(other, SingleMarker):
            return NotImplemented

        if self.name != other.name:
            return MultiMarker(self, other)
        if isinstance(other, MarkerExpression):
            new_values = OrderedSet([v for v in self.values if v in other.specifier])
            return self.replace(new_values)
        elif isinstance(other, EqualityMarkerUnion):
            new_values = self.values & other.values
            return self.replace(t.cast(OrderedSet, new_values))
        else:
            # intersection with InequalityMarkerUnion will be handled in the other class
            return NotImplemented

    def __or__(self, other: t.Any) -> BaseMarker:
        from dep_logic.markers.union import MarkerUnion

        if not isinstance(other, SingleMarker):
            return NotImplemented

        if self.name != other.name:
            return MarkerUnion(self, other)

        if isinstance(other, MarkerExpression):
            if other.op == "==":
                if other.value in self.values:
                    return self
                return replace(self, values=self.values | {other.value})
            if other.op == "!=":
                if other.value in self.values:
                    AnyMarker()
                return other
            if all(v in other.specifier for v in self.values):
                return other
            else:
                return MarkerUnion(self, other)
        elif isinstance(other, EqualityMarkerUnion):
            return replace(self, values=self.values | other.values)
        else:
            # intersection with InequalityMarkerUnion will be handled in the other class
            return NotImplemented

    __rand__ = __and__
    __ror__ = __or__


@dataclass(frozen=True, unsafe_hash=True, **DATACLASS_ARGS)
class InequalityMultiMarker(SingleMarker):
    name: str
    values: OrderedSet[str]

    def __str__(self) -> str:
        return " and ".join(f'{self.name} != "{value}"' for value in self.values)

    def replace(self, values: OrderedSet[str]) -> BaseMarker:
        if not values:
            return AnyMarker()
        if len(values) == 1:
            return MarkerExpression(self.name, "!=", values.peek())
        return replace(self, values=values)

    @property
    def complexity(self) -> tuple[int, ...]:
        return len(self.values), 1

    def __and__(self, other: t.Any) -> BaseMarker:
        from dep_logic.markers.multi import MultiMarker

        if not isinstance(other, SingleMarker):
            return NotImplemented
        if self.name != other.name:
            return MultiMarker(self, other)

        if isinstance(other, MarkerExpression):
            if other.op == "==":
                if other.value in self.values:
                    return EmptyMarker()
                return other
            elif other.op == "!=":
                if other.value in self.values:
                    return self
                return replace(self, values=self.values | {other.value})
            elif not any(v in other.specifier for v in self.values):
                return other
            else:
                return MultiMarker(self, other)
        elif isinstance(other, EqualityMarkerUnion):
            new_values = other.values - self.values
            return other.replace(t.cast(OrderedSet, new_values))
        else:
            assert isinstance(other, InequalityMultiMarker)
            return replace(self, values=self.values | other.values)

    def __or__(self, other: t.Any) -> BaseMarker:
        from dep_logic.markers.union import MarkerUnion

        if not isinstance(other, SingleMarker):
            return NotImplemented

        if self.name != other.name:
            return MarkerUnion(self, other)

        if isinstance(other, MarkerExpression):
            new_values = OrderedSet(
                [v for v in self.values if v not in other.specifier]
            )
            return self.replace(new_values)
        elif isinstance(other, EqualityMarkerUnion):
            new_values = self.values - other.values
            return self.replace(t.cast(OrderedSet, new_values))
        else:
            assert isinstance(other, InequalityMultiMarker)
            new_values = self.values & other.values
            return self.replace(t.cast(OrderedSet, new_values))

    __rand__ = __and__
    __ror__ = __or__


@functools.lru_cache(maxsize=None)
def _merge_single_markers(
    marker1: MarkerExpression,
    marker2: MarkerExpression,
    merge_class: type[MultiMarker | MarkerUnion],
) -> BaseMarker | None:
    from dep_logic.markers.multi import MultiMarker
    from dep_logic.markers.union import MarkerUnion

    if {marker1.name, marker2.name} == PYTHON_VERSION_MARKERS:
        return _merge_python_version_single_markers(marker1, marker2, merge_class)

    if marker1.name != marker2.name:
        return None

    # "extra" is special because it can have multiple values at the same time.
    # That's why we can only merge two "extra" markers if they have the same value.
    if marker1.name == "extra":
        if marker1.value != marker2.value:  # type: ignore[attr-defined]
            return None
    try:
        if merge_class is MultiMarker:
            result_specifier = marker1.specifier & marker2.specifier
        else:
            result_specifier = marker1.specifier | marker2.specifier
    except NotImplementedError:
        if marker1.op == marker2.op == "==" and merge_class is MarkerUnion:
            return EqualityMarkerUnion(
                marker1.name, OrderedSet([marker1.value, marker2.value])
            )
        elif marker1.op == marker2.op == "!=" and merge_class is MultiMarker:
            return InequalityMultiMarker(
                marker1.name, OrderedSet([marker1.value, marker2.value])
            )
        return None
    else:
        if result_specifier == marker1.specifier:
            return marker1
        if result_specifier == marker2.specifier:
            return marker2
        return MarkerExpression.from_specifier(marker1.name, result_specifier)


def _merge_python_version_single_markers(
    marker1: MarkerExpression,
    marker2: MarkerExpression,
    merge_class: type[MultiMarker | MarkerUnion],
) -> BaseMarker | None:
    from dep_logic.markers.multi import MultiMarker

    if marker1.name == "python_version":
        version_marker = marker1
        full_version_marker = marker2
    else:
        version_marker = marker2
        full_version_marker = marker1

    normalized_specifier = _normalize_python_version_specifier(version_marker)

    if merge_class is MultiMarker:
        merged = normalized_specifier & full_version_marker.specifier
    else:
        merged = normalized_specifier | full_version_marker.specifier
    if merged == normalized_specifier:
        # prefer original marker to avoid unnecessary changes
        return version_marker

    return MarkerExpression.from_specifier("python_full_version", merged)


def _normalize_python_version_specifier(marker: MarkerExpression) -> BaseSpecifier:
    from dep_logic.specifiers import parse_version_specifier

    op, value = marker.op, marker.value
    if op in ("in", "not in"):
        # skip this case, so in the following code value must be a dotted version string
        return marker.specifier
    splitted = [p.strip() for p in value.split(".")]
    if len(splitted) > 2 or "*" in splitted:
        return marker.specifier
    if op in ("==", "!="):
        splitted.append("*")
    elif op == ">":
        # python_version > '3.7' is equal to python_full_version >= '3.8.0'
        splitted[-1] = str(int(splitted[-1]) + 1)
        op = ">="
    elif op == "<=":
        # python_version <= '3.7' is equal to python_full_version < '3.8.0'
        splitted[-1] = str(int(splitted[-1]) + 1)
        op = "<"

    spec = parse_version_specifier(f'{op}{".".join(splitted)}')
    return spec
