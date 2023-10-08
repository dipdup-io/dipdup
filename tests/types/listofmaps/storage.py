from typing import Any

from pydantic import RootModel


class ListOfMapsStorage(RootModel[Any]):
    root: list[dict[str, str]]
