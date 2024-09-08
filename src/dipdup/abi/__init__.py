from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dipdup.package import DipDupPackage


class AbiManager(ABC):
    def __init__(self, package: DipDupPackage) -> None:
        self._package = package

    @abstractmethod
    def load(self) -> None: ...
