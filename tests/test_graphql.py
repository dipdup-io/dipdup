import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dipdup.datasources.graphql import GraphQLDatasource

@pytest.fixture
def mock_gql_client():
    with patch('dipdup.datasources.graphql.Client') as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.execute_async = AsyncMock()
        mock_client_instance.subscribe_async = AsyncMock()
        mock_client.return_value = mock_client_instance
        yield mock_client_instance

@pytest.mark.asyncio
async def test_graphql_datasource_connect(mock_gql_client):
    ds = GraphQLDatasource(url="https://example.com/graphql")
    await ds.connect()
    assert ds.client is not None

@pytest.mark.asyncio
async def test_graphql_datasource_execute_query(mock_gql_client):
    ds = GraphQLDatasource(url="https://example.com/graphql")
    await ds.connect()

    mock_gql_client.execute_async.return_value = {"data": {"blocks": [{"id": "1"}]}}

    with patch('builtins.open', MagicMock()) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "query { blocks { id } }"
        result = await ds.execute_query("getBlocks", variables={"limit": 1})

    assert result == {"data": {"blocks": [{"id": "1"}]}}
    mock_gql_client.execute_async.assert_called_once()

@pytest.mark.asyncio
async def test_graphql_datasource_subscribe(mock_gql_client):
    ds = GraphQLDatasource(url="https://example.com/graphql")
    await ds.connect()

    mock_gql_client.subscribe_async.return_value = [{"data": {"newBlock": {"id": "1"}}}]

    with patch('builtins.open', MagicMock()) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "subscription { newBlock { id } }"
        async for result in ds.subscribe("newBlocks"):
            assert result == {"data": {"newBlock": {"id": "1"}}}

    mock_gql_client.subscribe_async.assert_called_once()

@pytest.mark.asyncio
async def test_graphql_datasource_disconnect(mock_gql_client):
    ds = GraphQLDatasource(url="https://example.com/graphql")
    await ds.connect()
    await ds.disconnect()
    mock_gql_client.close_async.assert_called_once()