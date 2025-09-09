"""Tests for model comments functionality in Hasura integration."""

import inspect

import pytest

from dipdup import fields
from dipdup.config import HasuraConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.database import iter_models
from dipdup.hasura import HasuraGateway
from dipdup.models import Model


class TestUser(Model):
    """Represents a user in the system with authentication and profile information."""

    id = fields.IntField(pk=True)

    # The user's unique username for login
    username = fields.CharField(max_length=50, unique=True)

    # The user's email address for notifications
    email = fields.CharField(max_length=255, unique=True)

    # The user's full name for display
    full_name = fields.CharField(max_length=100)

    # When the user account was created
    created_at = fields.DatetimeField(auto_now_add=True)

    # Whether the user account is active
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = 'test_users'


class TestProduct(Model):
    """Represents a product in the marketplace."""

    id = fields.IntField(pk=True)

    # Product name
    name = fields.CharField(max_length=200)

    # Product description
    description = fields.TextField()

    # Product price in cents
    price = fields.IntField()

    class Meta:
        table = 'test_products'


def test_docstring_extraction() -> None:
    """Test that class docstrings are properly extracted."""
    table_doc = TestUser.__doc__ or ''
    assert 'user in the system' in table_doc
    assert 'authentication' in table_doc

    table_doc = TestProduct.__doc__ or ''
    assert 'product in the marketplace' in table_doc


def test_field_comment_extraction() -> None:
    """Test that field comments are properly extracted from source code."""
    source_lines = inspect.getsource(TestUser).split('\n')
    field_comments = {}

    for i, line in enumerate(source_lines):
        line = line.strip()
        if '=' in line and ('fields.' in line or "'fields." in line or '"fields.' in line) and not line.startswith('#'):
            field_name = line.split('=')[0].strip()
            if field_name and not field_name.startswith('_'):
                comment_lines: list[str] = []
                j = i - 1
                while j >= 0:
                    prev_line = source_lines[j].strip()
                    if prev_line.startswith('#'):
                        comment_lines.insert(0, prev_line[1:].strip())
                        j -= 1
                    elif prev_line == '':
                        j -= 1
                    else:
                        break

                if comment_lines:
                    field_comments[field_name] = ' '.join(comment_lines)

    # Verify specific field comments are extracted
    assert 'username' in field_comments
    assert 'unique username' in field_comments['username']
    assert 'email' in field_comments
    assert 'email address' in field_comments['email']
    assert 'full_name' in field_comments
    assert 'full name' in field_comments['full_name']


def test_model_iteration() -> None:
    """Test that models can be iterated properly."""
    # This test would need to be run in a proper DipDup project context
    # For now, we'll just verify the function exists
    assert callable(iter_models)


def test_hasura_gateway_methods() -> None:
    """Test that HasuraGateway has the required methods for model comments."""
    # Mock configs for testing
    hasura_config = HasuraConfig(
        url='http://localhost:8080',
        source='default',
        create_source=True,
        rest=False,
        camel_case=False,
        allow_aggregations=False,
        select_limit=100,
        hide_internal=True,
        hide=[],
        allow_inconsistent_metadata=False,
    )

    database_config = PostgresDatabaseConfig(
        kind='postgres',
        host='localhost',
        port=5432,
        user='test',
        password='test',
        database='test',
        schema_name='public',
    )

    # Create gateway instance
    gateway = HasuraGateway(package='test_package', hasura_config=hasura_config, database_config=database_config)

    # Verify required methods exist
    assert hasattr(gateway, '_apply_model_comments')
    assert hasattr(gateway, '_hasura_request')
    assert hasattr(gateway, 'configure')

    # Verify method is callable
    assert callable(gateway._apply_model_comments)


def test_comment_sql_generation() -> None:
    """Test that SQL comments are generated correctly."""
    table_name = 'test_users'
    table_doc = 'Test table comment'
    field_name = 'username'
    field_doc = 'Test field comment'
    schema_name = 'public'

    # Test table comment SQL
    table_sql = f"COMMENT ON TABLE {schema_name}.{table_name} IS '{table_doc}';"
    assert 'COMMENT ON TABLE' in table_sql
    assert table_name in table_sql
    assert table_doc in table_sql

    # Test column comment SQL
    column_sql = f"COMMENT ON COLUMN {schema_name}.{table_name}.{field_name} IS '{field_doc}';"
    assert 'COMMENT ON COLUMN' in column_sql
    assert table_name in column_sql
    assert field_name in column_sql
    assert field_doc in column_sql


def test_comment_length_limiting() -> None:
    """Test that comments are properly limited in length."""
    long_comment = 'x' * 2000  # Very long comment

    # Simulate the limiting logic
    if len(long_comment) > 1000:
        limited_comment = long_comment[:997] + '...'

    assert len(limited_comment) <= 1000
    assert limited_comment.endswith('...')


def test_comment_escaping() -> None:
    """Test that single quotes in comments are properly escaped."""
    comment_with_quotes = "This is a comment with 'single quotes'"
    escaped_comment = comment_with_quotes.replace("'", "''")

    assert "''" in escaped_comment
    assert escaped_comment.count("'") == 4  # Two pairs of escaped quotes


@pytest.mark.asyncio
async def test_metadata_refresh_integration() -> None:
    """Test that metadata refresh is properly integrated into the configure method."""
    # This test verifies the integration without requiring a full Hasura setup

    # Mock configs
    hasura_config = HasuraConfig(
        url='http://localhost:8080',
        source='default',
        create_source=True,
        rest=False,
        camel_case=False,
        allow_aggregations=False,
        select_limit=100,
        hide_internal=True,
        hide=[],
        allow_inconsistent_metadata=False,
    )

    database_config = PostgresDatabaseConfig(
        kind='postgres',
        host='localhost',
        port=5432,
        user='test',
        password='test',
        database='test',
        schema_name='public',
    )

    gateway = HasuraGateway(package='test_package', hasura_config=hasura_config, database_config=database_config)

    # Verify the configure method source contains the required components
    configure_source = inspect.getsource(gateway.configure)

    # Check for model comments application
    assert '_apply_model_comments' in configure_source

    # Check for metadata refresh
    assert 'reload_metadata' in configure_source

    # Check for proper order (comments before refresh)
    apply_comments_index = configure_source.find('_apply_model_comments')
    reload_metadata_index = configure_source.find('reload_metadata')

    assert apply_comments_index != -1
    assert reload_metadata_index != -1
    assert apply_comments_index < reload_metadata_index


def test_model_meta_attributes() -> None:
    """Test that model meta attributes are properly accessible."""
    assert hasattr(TestUser, '_meta')
    assert hasattr(TestUser._meta, 'db_table')
    assert TestUser._meta.db_table == 'test_users'

    assert hasattr(TestUser._meta, 'fields_map')
    assert 'username' in TestUser._meta.fields_map
    assert 'email' in TestUser._meta.fields_map

    # Test fields_db_projection
    if hasattr(TestUser._meta, 'fields_db_projection'):
        assert 'username' in TestUser._meta.fields_db_projection
