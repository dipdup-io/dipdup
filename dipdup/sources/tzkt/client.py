import httpx
from typing import Any, Dict, List, Optional

class TzktClient:
    def __init__(self, base_url: str = "https://api.tzkt.io/v1", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}/{endpoint}"
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    async def resolve_bigmap_ids(self, contract: str, path: str) -> List[int]:
        """
        Resolve bigmap ids from contract + path using TzKT bigmaps metadata endpoint.
        This allows us to use the more efficient bigmap.in filter afterwards.
        """
        params = {
            "contract.in": contract,
            "path.in": path,
            "select": "id",
            "limit": 100,
        }
        data = await self._get("bigmaps", params)
        return [int(item["id"]) for item in data if "id" in item]

    async def get_bigmaps(
        self,
        contract: Optional[str] = None,
        path: Optional[str] = None,
        bigmap_ids: Optional[List[int]] = None,
        **kwargs,
    ) -> Any:
        params: Dict[str, Any] = {}
        if bigmap_ids:
            params["bigmap.in"] = ",".join(str(i) for i in bigmap_ids)
        elif contract and path:
            # Optimize: prefer bigmap.in filtration
            resolved_ids = await self.resolve_bigmap_ids(contract, path)
            if resolved_ids:
                params["bigmap.in"] = ",".join(str(i) for i in resolved_ids)
            else:
                # fallback for safety
                params["contract.in"] = contract
                params["path.in"] = path
        else:
            if contract:
                params["contract.in"] = contract
            if path:
                params["path.in"] = path

        params.update(kwargs)
        return await self._get("bigmaps", params)

    async def get_bigmap_keys(
        self,
        contract: Optional[str] = None,
        path: Optional[str] = None,
        bigmap_ids: Optional[List[int]] = None,
        **kwargs,
    ) -> Any:
        """
        Fetch big map keys using bigmap.in when possible.
        Previously used contract.in + path.in which is less efficient.
        """
        if bigmap_ids:
            params = {"bigmap.in": ",".join(str(i) for i in bigmap_ids)}
        elif contract and path:
            resolved_ids = await self.resolve_bigmap_ids(contract, path)
            if resolved_ids:
                params = {"bigmap.in": ",".join(str(i) for i in resolved_ids)}
            else:
                params = {"contract.in": contract, "path.in": path}
        else:
            params = {}

        params.update(kwargs)
        return await self._get("bigmaps", params)

    async def get_bigmap_values(
        self,
        contract: Optional[str] = None,
        path: Optional[str] = None,
        bigmap_ids: Optional[List[int]] = None,
        **kwargs,
    ) -> Any:
        if bigmap_ids:
            params = {"bigmap.in": ",".join(str(i) for i in bigmap_ids)}
        elif contract and path:
            resolved_ids = await self.resolve_bigmap_ids(contract, path)
            params = {"bigmap.in": ",".join(str(i) for i in resolved_ids)} if resolved_ids else {"contract.in": contract, "path.in": path}
        else:
            params = {}

        params.update(kwargs)
        return await self._get("bigmaps", params)
