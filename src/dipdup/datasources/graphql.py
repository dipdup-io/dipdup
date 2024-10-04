# # src/dipdup/datasources/graphql.py
# from dipdup.datasources import Datasource # Update this path if necessary
# from dipdup.config import GraphQLDatasourceConfig  # Ensure this config is correctly defined
# from gql import gql, Client
# from gql.transport.aiohttp import AIOHTTPTransport

# class GraphQLDatasource(Datasource):
#     def __init__(self, config: GraphQLDatasourceConfig):
#         super().__init__(config)
#         self.url = config.url
#         self.client = None
#         self.subscription_query = None

#     async def connect(self):
#         transport = AIOHTTPTransport(url=self.url)
#         self.client = Client(transport=transport, fetch_schema_from_transport=True)

#     async def fetch_data(self, query: str):
#         async with self.client as session:
#             gql_query = gql(query)
#             return await session.execute(gql_query)

#     async def subscribe(self, subscription_query: str):
#         self.subscription_query = gql(subscription_query)
#         async with self.client as session:
#             async for result in session.subscribe(self.subscription_query):
#                 yield result

#     async def run(self) -> None:
#         await self.connect()

# src/dipdup/datasources/graphql.py
# src/dipdup/datasources/graphql.py
from dipdup.datasources import Datasource
from dipdup.config.graphql import GraphQLDatasourceConfig
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportException
from gql import GraphQLError

class GraphQLDatasource(Datasource):
    def __init__(self, config: GraphQLDatasourceConfig):
        super().__init__(config)
        self.client = None
        self.subscription_query = None

    async def connect(self):
        try:
            transport = AIOHTTPTransport(url=self.config.url)
            self.client = Client(transport=transport, fetch_schema_from_transport=True)
            await self.client.execute(gql("{ __type(name: \"Query\") { name } }"))  # Test connection
        except TransportException as e:
            # Handle transport-related errors (e.g., connection issues)
            print(f"Connection error: {e}")
            raise RuntimeError(f"Failed to connect to GraphQL API at {self.config.url}")
        except Exception as e:
            # Handle other exceptions
            print(f"An error occurred: {e}")
            raise RuntimeError("An unexpected error occurred while connecting.")

    async def fetch_data(self, query: str):
        try:
            async with self.client as session:
                gql_query = gql(query)
                response = await session.execute(gql_query)
                return response
        except GraphQLError as e:
            # Handle GraphQL errors (e.g., invalid query)
            print(f"GraphQL error: {e}")
            raise RuntimeError(f"GraphQL error occurred: {e}")
        except TransportException as e:
            # Handle transport-related errors
            print(f"Transport error during fetch: {e}")
            raise RuntimeError("Transport error occurred while fetching data.")
        except Exception as e:
            # Handle other exceptions
            print(f"An error occurred while fetching data: {e}")
            raise RuntimeError("An unexpected error occurred during data fetch.")

    async def subscribe(self, subscription_query: str):
        self.subscription_query = gql(subscription_query)
        try:
            async with self.client as session:
                async for result in session.subscribe(self.subscription_query):
                    yield result
        except GraphQLError as e:
            print(f"GraphQL error during subscription: {e}")
            raise RuntimeError(f"GraphQL error occurred during subscription: {e}")
        except TransportException as e:
            print(f"Transport error during subscription: {e}")
            raise RuntimeError("Transport error occurred during subscription.")
        except Exception as e:
            print(f"An error occurred during subscription: {e}")
            raise RuntimeError("An unexpected error occurred during subscription.")

    async def run(self) -> None:
        await self.connect()
