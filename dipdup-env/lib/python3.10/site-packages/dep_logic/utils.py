from __future__ import annotations

import functools
import itertools
import re
import sys
from typing import TYPE_CHECKING, AbstractSet, Iterable, Iterator, Protocol, TypeVar

_prefix_regex = re.compile(r"^([0-9]+)((?:a|b|c|rc)[0-9]+)$")

if TYPE_CHECKING:
    from typing import TypedDict

    from dep_logic.markers.base import BaseMarker

    class _DataClassArgs(TypedDict, total=False):
        slots: bool
        repr: bool


if sys.version_info >= (3, 10):
    DATACLASS_ARGS: _DataClassArgs = {"slots": True, "repr": False}
else:
    DATACLASS_ARGS = {"repr": False}


class Ident(Protocol):
    def __hash__(self) -> int: ...

    def __eq__(self, __value: object) -> bool: ...


T = TypeVar("T", bound=Ident)
V = TypeVar("V")


def version_split(version: str) -> list[str]:
    result: list[str] = []
    for item in version.split("."):
        match = _prefix_regex.search(item)
        if match:
            result.extend(match.groups())
        else:
            result.append(item)
    return result


def is_not_suffix(segment: str) -> bool:
    return not any(
        segment.startswith(prefix) for prefix in ("dev", "a", "b", "rc", "post")
    )


def flatten_items(items: Iterable[T], flatten_cls: type[Iterable[T]]) -> list[T]:
    flattened: list[T] = []
    for item in items:
        if isinstance(item, flatten_cls):
            for subitem in flatten_items(item, flatten_cls):
                if subitem not in flattened:
                    flattened.append(subitem)
        elif item not in flattened:
            flattened.append(item)
    return flattened


def first_different_index(
    iterable1: Iterable[object], iterable2: Iterable[object]
) -> int:
    index = 0
    for index, (item1, item2) in enumerate(zip(iterable1, iterable2)):
        if item1 != item2:
            return index
    return index + 1


def pad_zeros(parts: list[int], to_length: int) -> list[int]:
    if len(parts) >= to_length:
        return parts
    return parts + [0] * (to_length - len(parts))


@functools.lru_cache(maxsize=None)
def cnf(marker: BaseMarker) -> BaseMarker:
    from dep_logic.markers.multi import MultiMarker
    from dep_logic.markers.union import MarkerUnion

    """Transforms the marker into CNF (conjunctive normal form)."""
    if isinstance(marker, MarkerUnion):
        cnf_markers = [cnf(m) for m in marker.markers]
        sub_marker_lists = [
            m.markers if isinstance(m, MultiMarker) else [m] for m in cnf_markers
        ]
        return MultiMarker.of(
            *[MarkerUnion.of(*c) for c in itertools.product(*sub_marker_lists)]
        )

    if isinstance(marker, MultiMarker):
        return MultiMarker.of(*[cnf(m) for m in marker.markers])

    return marker


@functools.lru_cache(maxsize=None)
def dnf(marker: BaseMarker) -> BaseMarker:
    """Transforms the marker into DNF (disjunctive normal form)."""
    from dep_logic.markers.multi import MultiMarker
    from dep_logic.markers.union import MarkerUnion

    if isinstance(marker, MultiMarker):
        dnf_markers = [dnf(m) for m in marker.markers]
        sub_marker_lists = [
            m.markers if isinstance(m, MarkerUnion) else [m] for m in dnf_markers
        ]
        return MarkerUnion.of(
            *[MultiMarker.of(*c) for c in itertools.product(*sub_marker_lists)]
        )

    if isinstance(marker, MarkerUnion):
        return MarkerUnion.of(*[dnf(m) for m in marker.markers])

    return marker


def intersection(*markers: BaseMarker) -> BaseMarker:
    from dep_logic.markers.multi import MultiMarker

    return dnf(MultiMarker(*markers))


def union(*markers: BaseMarker) -> BaseMarker:
    from dep_logic.markers.multi import MultiMarker
    from dep_logic.markers.union import MarkerUnion

    # Sometimes normalization makes it more complicate instead of simple
    # -> choose candidate with the least complexity
    unnormalized: BaseMarker = MarkerUnion(*markers)
    while (
        isinstance(unnormalized, (MultiMarker, MarkerUnion))
        and len(unnormalized.markers) == 1
    ):
        unnormalized = unnormalized.markers[0]

    conjunction = cnf(unnormalized)
    if not isinstance(conjunction, MultiMarker):
        return conjunction

    disjunction = dnf(conjunction)
    if not isinstance(disjunction, MarkerUnion):
        return disjunction

    return min(disjunction, conjunction, unnormalized, key=lambda x: x.complexity)


_op_reflect_map = {
    "<": ">",
    "<=": ">=",
    ">": "<",
    ">=": "<=",
    "==": "==",
    "!=": "!=",
    "===": "===",
    "~=": "~=",
    "in": "in",
    "not in": "not in",
}


def get_reflect_op(op: str) -> str:
    return _op_reflect_map[op]


class OrderedSet(AbstractSet[T]):
    def __init__(self, iterable: Iterable[T]) -> None:
        self._data: list[T] = []
        for item in iterable:
            if item in self._data:
                continue
            self._data.append(item)

    def __hash__(self) -> int:
        return self._hash()

    def __contains__(self, obj: object) -> bool:
        return obj in self._data

    def __iter__(self) -> Iterator[T]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def peek(self) -> T:
        return self._data[0]
