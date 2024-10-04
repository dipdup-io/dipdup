# src/dipdup/tests/test_graphql.py
import asyncio
from dipdup.config.graphql import GraphQLDatasourceConfig
from dipdup.datasources.graphql import GraphQLDatasource

async def main():
    try:
        config = GraphQLDatasourceConfig(url="https://your-graphql-api.com")
        datasource = GraphQLDatasource(config)
        await datasource.connect()
        
        # Test fetching valid data
        response = await datasource.fetch_data("{ yourQueryHere }")
        print(response)

        # Test with an invalid query to trigger error handling
        invalid_response = await datasource.fetch_data("{ invalidQuery }")
        print(invalid_response)

    except RuntimeError as e:
        print(f"Runtime error caught: {e}")

if __name__ == "__main__":
    asyncio.run(main())
