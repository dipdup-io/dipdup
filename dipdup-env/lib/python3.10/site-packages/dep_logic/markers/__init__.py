# Adapted from poetry/core/version/markers.py
# The original work is published under the MIT license.
# Copyright (c) 2020 Sébastien Eustace
# Adapted by Frost Ming (c) 2023

from __future__ import annotations

import functools
from typing import TYPE_CHECKING

from packaging.markers import InvalidMarker as _InvalidMarker
from packaging.markers import Marker as _Marker

from dep_logic.markers.any import AnyMarker
from dep_logic.markers.base import BaseMarker
from dep_logic.markers.empty import EmptyMarker
from dep_logic.markers.multi import MultiMarker
from dep_logic.markers.single import MarkerExpression
from dep_logic.markers.union import MarkerUnion
from dep_logic.utils import get_reflect_op

if TYPE_CHECKING:
    from typing import List, Literal, Tuple, Union

    from packaging.markers import Op, Value, Variable

    _ParsedMarker = Tuple[Variable, Op, Value]
    _ParsedMarkers = Union[
        _ParsedMarker, List[Union["_ParsedMarkers", Literal["or", "and"]]]
    ]


__all__ = [
    "parse_marker",
    "from_pkg_marker",
    "InvalidMarker",
    "BaseMarker",
    "AnyMarker",
    "EmptyMarker",
    "MarkerExpression",
    "MarkerUnion",
    "MultiMarker",
]


class InvalidMarker(ValueError):
    """
    An invalid marker was found, users should refer to PEP 508.
    """


@functools.lru_cache(maxsize=None)
def parse_marker(marker: str) -> BaseMarker:
    if marker == "<empty>":
        return EmptyMarker()

    if not marker or marker == "*":
        return AnyMarker()
    try:
        parsed = _Marker(marker)
    except _InvalidMarker as e:
        raise InvalidMarker(str(e)) from e

    markers = _build_markers(parsed._markers)

    return markers


def from_pkg_marker(marker: _Marker) -> BaseMarker:
    return _build_markers(marker._markers)


def _build_markers(markers: _ParsedMarkers) -> BaseMarker:
    from packaging.markers import Variable

    if isinstance(markers, tuple):
        if isinstance(markers[0], Variable):
            name, op, value, reversed = (
                str(markers[0]),
                str(markers[1]),
                str(markers[2]),
                False,
            )
        else:
            # in reverse order
            name, op, value, reversed = (
                str(markers[2]),
                get_reflect_op(str(markers[1])),
                str(markers[0]),
                True,
            )
        return MarkerExpression(name, op, value, reversed)
    or_groups: list[BaseMarker] = [AnyMarker()]
    for item in markers:
        if item == "or":
            or_groups.append(AnyMarker())
        elif item == "and":
            continue
        else:
            or_groups[-1] &= _build_markers(item)
    return MarkerUnion.of(*or_groups)
