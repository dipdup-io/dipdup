from __future__ import annotations

from dep_logic.markers.base import BaseMarker


class AnyMarker(BaseMarker):
    def __and__(self, other: BaseMarker) -> BaseMarker:
        return other

    __rand__ = __and__

    def __or__(self, other: BaseMarker) -> BaseMarker:
        return self

    __ror__ = __or__

    def is_any(self) -> bool:
        return True

    def evaluate(self, environment: dict[str, str] | None = None) -> bool:
        return True

    def without_extras(self) -> BaseMarker:
        return self

    def exclude(self, marker_name: str) -> BaseMarker:
        return self

    def only(self, *marker_names: str) -> BaseMarker:
        return self

    def __str__(self) -> str:
        return ""

    def __repr__(self) -> str:
        return "<AnyMarker>"

    def __hash__(self) -> int:
        return hash("any")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseMarker):
            return NotImplemented

        return isinstance(other, AnyMarker)
