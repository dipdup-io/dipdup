from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from dep_logic.markers.any import AnyMarker
from dep_logic.markers.base import BaseMarker
from dep_logic.markers.empty import EmptyMarker
from dep_logic.markers.multi import MultiMarker
from dep_logic.markers.single import SingleMarker
from dep_logic.utils import DATACLASS_ARGS, flatten_items, intersection, union


@dataclass(init=False, frozen=True, unsafe_hash=True, **DATACLASS_ARGS)
class MarkerUnion(BaseMarker):
    markers: tuple[BaseMarker, ...]

    def __init__(self, *markers: BaseMarker) -> None:
        object.__setattr__(self, "markers", tuple(flatten_items(markers, MarkerUnion)))

    def __iter__(self) -> Iterator[BaseMarker]:
        return iter(self.markers)

    @property
    def complexity(self) -> tuple[int, ...]:
        return tuple(sum(c) for c in zip(*(m.complexity for m in self.markers)))

    @classmethod
    def of(cls, *markers: BaseMarker) -> BaseMarker:
        new_markers = flatten_items(markers, MarkerUnion)
        old_markers: list[BaseMarker] = []

        while old_markers != new_markers:
            old_markers = new_markers
            new_markers = []
            for marker in old_markers:
                if marker in new_markers:
                    continue

                if marker.is_empty():
                    continue

                included = False
                for i, mark in enumerate(new_markers):
                    # If we have a SingleMarker then with any luck after union it'll
                    # become another SingleMarker.
                    if isinstance(mark, SingleMarker):
                        new_marker = mark | marker
                        if new_marker.is_any():
                            return AnyMarker()

                        if isinstance(new_marker, SingleMarker):
                            new_markers[i] = new_marker
                            included = True
                            break

                    # If we have a MultiMarker then we can look for the simplifications
                    # implemented in union_simplify().
                    elif isinstance(mark, MultiMarker):
                        union = mark.union_simplify(marker)
                        if union is not None:
                            new_markers[i] = union
                            included = True
                            break

                if included:
                    # flatten again because union_simplify may return a union
                    new_markers = flatten_items(new_markers, MarkerUnion)
                    continue

                new_markers.append(marker)

        if any(m.is_any() for m in new_markers):
            return AnyMarker()

        if not new_markers:
            return EmptyMarker()

        if len(new_markers) == 1:
            return new_markers[0]

        return MarkerUnion(*new_markers)

    def __and__(self, other: BaseMarker) -> BaseMarker:
        return intersection(self, other)

    def __or__(self, other: BaseMarker) -> BaseMarker:
        return union(self, other)

    __rand__ = __and__
    __ror__ = __or__

    def intersect_simplify(self, other: BaseMarker) -> BaseMarker | None:
        """
        Finds a couple of easy simplifications for intersection on MarkerUnions:

            - intersection with any marker that appears as part of the union is just
              that marker

            - intersection between two markerunions where one is contained by the other
              is just the smaller of the two

            - intersection between two markerunions where there are some common markers
              and the intersection of unique markers is not a single marker
        """
        if other in self.markers:
            return other

        if isinstance(other, MarkerUnion):
            our_markers = set(self.markers)
            their_markers = set(other.markers)

            if our_markers.issubset(their_markers):
                return self

            if their_markers.issubset(our_markers):
                return other

            shared_markers = our_markers.intersection(their_markers)
            if not shared_markers:
                return None

            unique_markers = our_markers - their_markers
            other_unique_markers = their_markers - our_markers
            unique_intersection = MarkerUnion(*unique_markers) & MarkerUnion(
                *other_unique_markers
            )

            if isinstance(unique_intersection, (SingleMarker, EmptyMarker)):
                # Use list instead of set for deterministic order.
                common_markers = [
                    marker for marker in self.markers if marker in shared_markers
                ]
                return unique_intersection | MarkerUnion(*common_markers)

        return None

    def evaluate(self, environment: dict[str, str] | None = None) -> bool:
        return any(m.evaluate(environment) for m in self.markers)

    def without_extras(self) -> BaseMarker:
        return self.exclude("extra")

    def exclude(self, marker_name: str) -> BaseMarker:
        new_markers = []

        for m in self.markers:
            if isinstance(m, SingleMarker) and m.name == marker_name:
                # The marker is not relevant since it must be excluded
                continue

            marker = m.exclude(marker_name)
            new_markers.append(marker)

        if not new_markers:
            # All markers were the excluded marker.
            return AnyMarker()

        return self.of(*new_markers)

    def only(self, *marker_names: str) -> BaseMarker:
        return self.of(*(m.only(*marker_names) for m in self.markers))

    def __str__(self) -> str:
        return " or ".join(str(m) for m in self.markers)
