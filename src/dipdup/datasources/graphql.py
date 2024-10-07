import asyncio
from typing import Any, Dict, List, Optional, AsyncIterator
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from dipdup.datasources import Datasource

class GraphQLDatasource(Datasource):
    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        query_path: str = "graphql/",
    ):
        super().__init__()
        self.url = url
        self.headers = headers or {}
        self.query_path = query_path
        self.client: Optional[Client] = None

    async def connect(self):
        transport = AIOHTTPTransport(url=self.url, headers=self.headers)
        self.client = Client(transport=transport, fetch_schema_from_transport=True)

    async def disconnect(self):
        if self.client:
            await self.client.close_async()

    async def execute_query(self, query_name: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("GraphQL client is not initialized. Call connect() first.")

        query_path = f"{self.query_path}{query_name}.graphql"
        with open(query_path, 'r') as file:
            query_string = file.read()

        query = gql(query_string)
        result = await self.client.execute_async(query, variable_values=variables)
        return result

    async def subscribe(self, query_name: str, variables: Optional[Dict[str, Any]] = None) -> AsyncIterator[Dict[str, Any]]:
        if not self.client:
            raise RuntimeError("GraphQL client is not initialized. Call connect() first.")

        query_path = f"{self.query_path}{query_name}.graphql"
        with open(query_path, 'r') as file:
            query_string = file.read()

        query = gql(query_string)
        async for result in self.client.subscribe_async(query, variable_values=variables):
            yield result