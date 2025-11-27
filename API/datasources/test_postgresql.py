"""
Unit tests for PostgreSQL connector
Tests the PostgreSQL data source connector implementation
"""

import pytest
import os
import tempfile
import csv
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

# Mock psycopg2 before importing postgresql module
psycopg2_mock = MagicMock()
psycopg2_mock.pool = MagicMock()
psycopg2_mock.sql = MagicMock()
psycopg2_mock.extensions = MagicMock()
psycopg2_mock.extras = MagicMock()
psycopg2_mock.errors = MagicMock()

# Create proper exception classes that inherit from BaseException
class MockOperationalError(Exception):
    pass

class MockError(Exception):
    pass

class MockQueryCanceled(Exception):
    pass

psycopg2_mock.OperationalError = MockOperationalError
psycopg2_mock.Error = MockError
psycopg2_mock.errors.QueryCanceled = MockQueryCanceled

import sys
sys.modules['psycopg2'] = psycopg2_mock
sys.modules['psycopg2.pool'] = psycopg2_mock.pool
sys.modules['psycopg2.sql'] = psycopg2_mock.sql
sys.modules['psycopg2.extensions'] = psycopg2_mock.extensions
sys.modules['psycopg2.extras'] = psycopg2_mock.extras
sys.modules['psycopg2.errors'] = psycopg2_mock.errors

from API.datasources.postgresql import PostgreSQLConnector
from API.datasources.base import (
    DataSourceConfig,
    DataSourceType,
    ConnectionError as DSConnectionError,
    AuthenticationError,
    DataFetchError,
)


@pytest.fixture
def pg_config():
    """Create a test PostgreSQL configuration"""
    return DataSourceConfig(
        id="test-pg",
        type=DataSourceType.POSTGRESQL,
        name="Test PostgreSQL",
        config={
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'user': 'testuser',
            'password': 'testpass',
            'query_timeout': 30,
            'max_result_rows': 10000,
            'read_only': True,
        }
    )


@pytest.fixture
def pg_config_connection_string():
    """Create a test PostgreSQL configuration with connection string"""
    return DataSourceConfig(
        id="test-pg-connstr",
        type=DataSourceType.POSTGRESQL,
        name="Test PostgreSQL ConnStr",
        config={
            'connection_string': 'postgresql://testuser:testpass@localhost:5432/testdb',
            'read_only': True,
        }
    )


@pytest.fixture
def mock_connection_pool():
    """Create a mock connection pool"""
    pool = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    
    pool.getconn.return_value = conn
    conn.cursor.return_value = cursor
    cursor.fetchone.return_value = ('PostgreSQL 14.0',)
    
    return pool, conn, cursor


class TestPostgreSQLConnectorInit:
    """Test PostgreSQL connector initialization"""
    
    def test_init_with_valid_config(self, pg_config):
        """Test initialization with valid configuration"""
        connector = PostgreSQLConnector(pg_config)
        
        assert connector.config == pg_config
        assert connector._connection is None
        assert connector._connection_pool is None
        assert connector._query_timeout == 30
        assert connector._max_result_rows == 10000
        assert connector._read_only is True
        print("✓ PostgreSQL connector initializes correctly")
    
    def test_init_with_defaults(self):
        """Test initialization with default values"""
        config = DataSourceConfig(
            id="test-pg",
            type=DataSourceType.POSTGRESQL,
            name="Test PostgreSQL",
            config={
                'host': 'localhost',
                'database': 'testdb',
                'user': 'testuser',
                'password': 'testpass',
            }
        )
        
        connector = PostgreSQLConnector(config)
        
        assert connector._query_timeout == 30
        assert connector._max_result_rows == 10000
        assert connector._read_only is True
        print("✓ PostgreSQL connector uses default values correctly")


class TestPostgreSQLConnectorConnection:
    """Test PostgreSQL connector connection management"""
    
    @pytest.mark.asyncio
    async def test_connect_with_individual_params(self, pg_config, mock_connection_pool):
        """Test connection with individual parameters"""
        pool, conn, cursor = mock_connection_pool
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config)
            result = await connector.connect()
            
            assert result is True
            assert connector.is_connected()
            assert connector._connection_pool == pool
            
            # Verify connection pool was created with correct params
            psycopg2_mock.pool.SimpleConnectionPool.assert_called_once()
            call_kwargs = psycopg2_mock.pool.SimpleConnectionPool.call_args[1]
            assert call_kwargs['host'] == 'localhost'
            assert call_kwargs['port'] == 5432
            assert call_kwargs['database'] == 'testdb'
            assert call_kwargs['user'] == 'testuser'
            assert call_kwargs['password'] == 'testpass'
            
            print("✓ Connects successfully with individual parameters")
    
    @pytest.mark.asyncio
    async def test_connect_with_connection_string(self, pg_config_connection_string, mock_connection_pool):
        """Test connection with connection string"""
        pool, conn, cursor = mock_connection_pool
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config_connection_string)
            result = await connector.connect()
            
            assert result is True
            assert connector.is_connected()
            
            # Verify connection pool was created with DSN
            call_kwargs = psycopg2_mock.pool.SimpleConnectionPool.call_args[1]
            assert 'dsn' in call_kwargs
            
            print("✓ Connects successfully with connection string")
    
    @pytest.mark.asyncio
    async def test_connect_missing_required_params(self):
        """Test connection fails with missing required parameters"""
        config = DataSourceConfig(
            id="test-pg",
            type=DataSourceType.POSTGRESQL,
            name="Test PostgreSQL",
            config={
                'host': 'localhost',
                # Missing database, user, password
            }
        )
        
        connector = PostgreSQLConnector(config)
        
        with pytest.raises(DSConnectionError, match="'database' is required"):
            await connector.connect()
        
        print("✓ Raises error for missing required parameters")
    
    @pytest.mark.asyncio
    async def test_connect_authentication_failure(self, pg_config):
        """Test connection fails with authentication error"""
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool') as mock_pool:
            mock_pool.side_effect = MockOperationalError("authentication failed")
            
            connector = PostgreSQLConnector(pg_config)
            
            with pytest.raises(AuthenticationError, match="Failed to connect to PostgreSQL"):
                await connector.connect()
        
        print("✓ Raises AuthenticationError on authentication failure")
    
    @pytest.mark.asyncio
    async def test_disconnect(self, pg_config, mock_connection_pool):
        """Test disconnection"""
        pool, conn, cursor = mock_connection_pool
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config)
            await connector.connect()
            
            await connector.disconnect()
            
            assert connector._connection_pool is None
            assert connector._connection is None
            assert not connector.is_connected()
            pool.closeall.assert_called_once()
            
            print("✓ Disconnects and cleans up resources")
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, pg_config, mock_connection_pool):
        """Test connection test succeeds"""
        pool, conn, cursor = mock_connection_pool
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config)
            await connector.connect()
            
            result = await connector.test_connection()
            
            assert result is True
            cursor.execute.assert_called_with("SELECT 1;")
            
            print("✓ Connection test succeeds when connected")
    
    @pytest.mark.asyncio
    async def test_test_connection_not_connected(self, pg_config, mock_connection_pool):
        """Test connection test when not connected"""
        pool, conn, cursor = mock_connection_pool
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config)
            
            result = await connector.test_connection()
            
            assert result is True  # Should connect and test
            
            print("✓ Connection test connects if not already connected")


class TestPostgreSQLConnectorReadOnly:
    """Test read-only enforcement"""
    
    def test_is_write_query_detects_insert(self, pg_config):
        """Test detection of INSERT queries"""
        connector = PostgreSQLConnector(pg_config)
        
        assert connector._is_write_query("INSERT INTO users VALUES (1, 'test')")
        assert connector._is_write_query("insert into users values (1, 'test')")
        print("✓ Detects INSERT queries")
    
    def test_is_write_query_detects_update(self, pg_config):
        """Test detection of UPDATE queries"""
        connector = PostgreSQLConnector(pg_config)
        
        assert connector._is_write_query("UPDATE users SET name = 'test'")
        assert connector._is_write_query("update users set name = 'test'")
        print("✓ Detects UPDATE queries")
    
    def test_is_write_query_detects_delete(self, pg_config):
        """Test detection of DELETE queries"""
        connector = PostgreSQLConnector(pg_config)
        
        assert connector._is_write_query("DELETE FROM users WHERE id = 1")
        assert connector._is_write_query("delete from users where id = 1")
        print("✓ Detects DELETE queries")
    
    def test_is_write_query_detects_drop(self, pg_config):
        """Test detection of DROP queries"""
        connector = PostgreSQLConnector(pg_config)
        
        assert connector._is_write_query("DROP TABLE users")
        assert connector._is_write_query("drop table users")
        print("✓ Detects DROP queries")
    
    def test_is_write_query_detects_create(self, pg_config):
        """Test detection of CREATE queries"""
        connector = PostgreSQLConnector(pg_config)
        
        assert connector._is_write_query("CREATE TABLE users (id INT)")
        assert connector._is_write_query("create table users (id int)")
        print("✓ Detects CREATE queries")
    
    def test_is_write_query_allows_select(self, pg_config):
        """Test SELECT queries are allowed"""
        connector = PostgreSQLConnector(pg_config)
        
        assert not connector._is_write_query("SELECT * FROM users")
        assert not connector._is_write_query("select * from users")
        print("✓ Allows SELECT queries")
    
    def test_is_write_query_ignores_comments(self, pg_config):
        """Test comments are ignored in write detection"""
        connector = PostgreSQLConnector(pg_config)
        
        # Comment with write command should not trigger
        query = """
        -- This is a comment with INSERT
        SELECT * FROM users
        """
        assert not connector._is_write_query(query)
        
        # Block comment
        query = """
        /* This is a comment with DELETE */
        SELECT * FROM users
        """
        assert not connector._is_write_query(query)
        
        print("✓ Ignores write commands in comments")


class TestPostgreSQLConnectorListItems:
    """Test listing tables and views"""
    
    @pytest.mark.asyncio
    async def test_list_items_success(self, pg_config, mock_connection_pool):
        """Test listing tables successfully"""
        pool, conn, cursor = mock_connection_pool
        
        # Mock table listing results
        cursor.fetchall.return_value = [
            {'table_name': 'users', 'table_type': 'BASE TABLE', 'table_schema': 'public'},
            {'table_name': 'orders', 'table_type': 'BASE TABLE', 'table_schema': 'public'},
            {'table_name': 'user_view', 'table_type': 'VIEW', 'table_schema': 'public'},
        ]
        
        # Mock row count queries
        cursor.fetchone.side_effect = [
            ('PostgreSQL 14.0',),  # For connection test
            {'count': 100},  # users table
            {'count': 50},   # orders table
        ]
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config)
            await connector.connect()
            
            items = await connector.list_items()
            
            assert len(items) == 3
            assert items[0].name == 'users'
            assert items[0].path == 'public.users'
            assert items[0].size == 100
            assert items[0].metadata['table_type'] == 'BASE TABLE'
            
            assert items[1].name == 'orders'
            assert items[2].name == 'user_view'
            
            print("✓ Lists tables and views successfully")
    
    @pytest.mark.asyncio
    async def test_list_items_with_schema(self, pg_config, mock_connection_pool):
        """Test listing tables from specific schema"""
        pool, conn, cursor = mock_connection_pool
        
        cursor.fetchall.return_value = [
            {'table_name': 'products', 'table_type': 'BASE TABLE', 'table_schema': 'sales'},
        ]
        cursor.fetchone.side_effect = [
            ('PostgreSQL 14.0',),
            {'count': 200},
        ]
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config)
            await connector.connect()
            
            items = await connector.list_items(path='sales')
            
            assert len(items) == 1
            assert items[0].path == 'sales.products'
            
            print("✓ Lists tables from specific schema")
    
    @pytest.mark.asyncio
    async def test_list_items_not_connected(self, pg_config):
        """Test listing fails when not connected"""
        connector = PostgreSQLConnector(pg_config)
        
        with pytest.raises(DataFetchError, match="Not connected"):
            await connector.list_items()
        
        print("✓ Raises error when not connected")


class TestPostgreSQLConnectorFetchData:
    """Test query execution and data fetching"""
    
    @pytest.mark.asyncio
    async def test_fetch_data_success(self, pg_config, mock_connection_pool):
        """Test executing query and saving results"""
        pool, conn, cursor = mock_connection_pool
        
        # Mock query results
        cursor.fetchmany.return_value = [
            {'id': 1, 'name': 'Alice'},
            {'id': 2, 'name': 'Bob'},
        ]
        cursor.fetchone.side_effect = [
            ('PostgreSQL 14.0',),  # Connection test
            None,  # No more rows after fetchmany
        ]
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config)
            await connector.connect()
            
            with tempfile.TemporaryDirectory() as workspace:
                query = "SELECT * FROM users"
                result_path = await connector.fetch_data(query, workspace)
                
                assert os.path.exists(result_path)
                assert result_path.endswith('.csv')
                
                # Verify CSV contents
                with open(result_path, 'r') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    assert len(rows) == 2
                    assert rows[0]['id'] == '1'
                    assert rows[0]['name'] == 'Alice'
                
                print("✓ Executes query and saves results to CSV")
    
    @pytest.mark.asyncio
    async def test_fetch_data_empty_results(self, pg_config, mock_connection_pool):
        """Test query with no results"""
        pool, conn, cursor = mock_connection_pool
        
        cursor.fetchmany.return_value = []
        cursor.fetchone.side_effect = [
            ('PostgreSQL 14.0',),
            None,
        ]
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config)
            await connector.connect()
            
            with tempfile.TemporaryDirectory() as workspace:
                query = "SELECT * FROM empty_table"
                result_path = await connector.fetch_data(query, workspace)
                
                assert os.path.exists(result_path)
                
                # Verify empty file
                with open(result_path, 'r') as f:
                    content = f.read()
                    assert content == ""
                
                print("✓ Handles empty query results")
    
    @pytest.mark.asyncio
    async def test_fetch_data_write_query_blocked(self, pg_config, mock_connection_pool):
        """Test write queries are blocked in read-only mode"""
        pool, conn, cursor = mock_connection_pool
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config)
            await connector.connect()
            
            with tempfile.TemporaryDirectory() as workspace:
                query = "DELETE FROM users WHERE id = 1"
                
                with pytest.raises(DataFetchError, match="Write operations are not allowed"):
                    await connector.fetch_data(query, workspace)
                
                print("✓ Blocks write queries in read-only mode")
    
    @pytest.mark.asyncio
    async def test_fetch_data_not_connected(self, pg_config):
        """Test fetch fails when not connected"""
        connector = PostgreSQLConnector(pg_config)
        
        with tempfile.TemporaryDirectory() as workspace:
            with pytest.raises(DataFetchError, match="Not connected"):
                await connector.fetch_data("SELECT 1", workspace)
        
        print("✓ Raises error when not connected")
    
    @pytest.mark.asyncio
    async def test_fetch_data_query_timeout(self, pg_config, mock_connection_pool):
        """Test query timeout handling"""
        pool, conn, cursor = mock_connection_pool
        
        # Reset cursor for this test
        cursor.execute.side_effect = None
        cursor.execute.reset_mock()
        
        # Mock timeout error - need to raise on the actual query, not the setup
        call_count = [0]
        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call during connect - version check
                return None
            elif call_count[0] == 2:
                # Second call - SET statement_timeout
                return None
            else:
                # Third call - actual query
                raise MockQueryCanceled("timeout")
        
        cursor.execute.side_effect = execute_side_effect
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config)
            await connector.connect()
            
            with tempfile.TemporaryDirectory() as workspace:
                with pytest.raises(DataFetchError, match="Query timeout"):
                    await connector.fetch_data("SELECT * FROM huge_table", workspace)
        
        print("✓ Handles query timeout")


class TestPostgreSQLConnectorGetMetadata:
    """Test table metadata retrieval"""
    
    @pytest.mark.asyncio
    async def test_get_metadata_success(self, pg_config, mock_connection_pool):
        """Test retrieving table metadata"""
        pool, conn, cursor = mock_connection_pool
        
        # Mock metadata results
        cursor.fetchall.side_effect = [
            # Column information
            [
                {
                    'column_name': 'id',
                    'data_type': 'integer',
                    'character_maximum_length': None,
                    'is_nullable': 'NO',
                    'column_default': "nextval('users_id_seq'::regclass)"
                },
                {
                    'column_name': 'name',
                    'data_type': 'character varying',
                    'character_maximum_length': 255,
                    'is_nullable': 'YES',
                    'column_default': None
                },
            ],
            # Primary keys
            [{'attname': 'id'}],
        ]
        
        cursor.fetchone.side_effect = [
            ('PostgreSQL 14.0',),  # Connection test
            {'count': 100},  # Row count
        ]
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config)
            await connector.connect()
            
            metadata = await connector.get_metadata('users')
            
            assert metadata['table_name'] == 'users'
            assert metadata['schema'] == 'public'
            assert metadata['row_count'] == 100
            assert len(metadata['columns']) == 2
            assert metadata['columns'][0]['column_name'] == 'id'
            assert metadata['primary_keys'] == ['id']
            
            print("✓ Retrieves table metadata successfully")
    
    @pytest.mark.asyncio
    async def test_get_metadata_with_schema(self, pg_config, mock_connection_pool):
        """Test retrieving metadata with schema prefix"""
        pool, conn, cursor = mock_connection_pool
        
        cursor.fetchall.side_effect = [
            [{'column_name': 'id', 'data_type': 'integer', 'character_maximum_length': None,
              'is_nullable': 'NO', 'column_default': None}],
            [],
        ]
        cursor.fetchone.side_effect = [
            ('PostgreSQL 14.0',),
            {'count': 50},
        ]
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config)
            await connector.connect()
            
            metadata = await connector.get_metadata('sales.products')
            
            assert metadata['table_name'] == 'products'
            assert metadata['schema'] == 'sales'
            
            print("✓ Handles schema-qualified table names")
    
    @pytest.mark.asyncio
    async def test_get_metadata_table_not_found(self, pg_config, mock_connection_pool):
        """Test metadata retrieval for non-existent table"""
        pool, conn, cursor = mock_connection_pool
        
        cursor.fetchall.return_value = []  # No columns found
        cursor.fetchone.return_value = ('PostgreSQL 14.0',)
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config)
            await connector.connect()
            
            with pytest.raises(DataFetchError, match="Table .* not found"):
                await connector.get_metadata('nonexistent')
        
        print("✓ Raises error for non-existent table")


class TestPostgreSQLConnectorTablePreview:
    """Test table preview functionality"""
    
    @pytest.mark.asyncio
    async def test_get_table_preview_success(self, pg_config, mock_connection_pool):
        """Test getting table preview"""
        pool, conn, cursor = mock_connection_pool
        
        cursor.fetchall.return_value = [
            {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
            {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},
        ]
        cursor.fetchone.return_value = ('PostgreSQL 14.0',)
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config)
            await connector.connect()
            
            preview = await connector.get_table_preview('users', limit=2)
            
            assert len(preview) == 2
            assert preview[0]['id'] == 1
            assert preview[0]['name'] == 'Alice'
            
            print("✓ Gets table preview successfully")
    
    @pytest.mark.asyncio
    async def test_get_table_preview_with_schema(self, pg_config, mock_connection_pool):
        """Test preview with schema-qualified table name"""
        pool, conn, cursor = mock_connection_pool
        
        cursor.fetchall.return_value = [{'id': 1, 'product': 'Widget'}]
        cursor.fetchone.return_value = ('PostgreSQL 14.0',)
        
        with patch('API.datasources.postgresql.pool.SimpleConnectionPool', return_value=pool):
            connector = PostgreSQLConnector(pg_config)
            await connector.connect()
            
            preview = await connector.get_table_preview('sales.products', limit=5)
            
            assert len(preview) == 1
            
            print("✓ Handles schema-qualified names in preview")


def run_all_tests():
    """Run all tests and print summary"""
    print("\n" + "="*70)
    print("Running PostgreSQL Connector Tests")
    print("="*70 + "\n")
    
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == '__main__':
    run_all_tests()
