from __future__ import annotations

from typing import Optional

from dipdup.models.index import Index, IndexStatus


class DipDupContext:
    def __init__(self, storage, indexes: dict[str, Index] | None = None):
        self.storage = storage
        self.indexes = indexes or {}

    async def get_index(self, name: str) -> Index:
        if name not in self.indexes:
            raise KeyError(f"Index {name} not found")
        return self.indexes[name]

    async def update_index(
        self,
        name: str,
        status: Optional[IndexStatus] = None,
        properties: Optional[dict[str, Any]] = None,
    ) -> Index:
        index = await self.get_index(name)

        if status is not None:
            index.status = status

        if properties:
            if not isinstance(index.properties, dict):
                index.properties = {}
            index.properties.update(properties)

        await self.storage.update_index(index)
        self.indexes[name] = index
        return index
