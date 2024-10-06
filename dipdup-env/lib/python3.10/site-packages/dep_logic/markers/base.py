from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Any


class BaseMarker(metaclass=ABCMeta):
    @property
    def complexity(self) -> tuple[int, ...]:
        """
        The first number is the number of marker expressions,
        and the second number is 1 if the marker is single-like.
        """
        return 1, 1

    @abstractmethod
    def __and__(self, other: Any) -> BaseMarker:
        raise NotImplementedError

    @abstractmethod
    def __or__(self, other: Any) -> BaseMarker:
        raise NotImplementedError

    def is_any(self) -> bool:
        return False

    def is_empty(self) -> bool:
        return False

    @abstractmethod
    def evaluate(self, environment: dict[str, str] | None = None) -> bool:
        raise NotImplementedError

    @abstractmethod
    def without_extras(self) -> BaseMarker:
        raise NotImplementedError

    @abstractmethod
    def exclude(self, marker_name: str) -> BaseMarker:
        raise NotImplementedError

    @abstractmethod
    def only(self, *marker_names: str) -> BaseMarker:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self}>"

    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError
