"""
PostgreSQL Database Connector
Implements data source connector for PostgreSQL databases
"""

import os
import logging
import csv
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

try:
    import psycopg2
    from psycopg2 import pool, sql, extensions
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None

from .base import (
    DataSourceConnector,
    DataSourceConfig,
    DataItem,
    ConnectionError as DSConnectionError,
    AuthenticationError,
    DataFetchError,
)

logger = logging.getLogger(__name__)


class PostgreSQLConnector(DataSourceConnector):
    """Connector for PostgreSQL databases
    
    This connector provides access to PostgreSQL databases, allowing
    listing tables, executing queries, and retrieving schema information.
    
    Configuration parameters:
        - host: Database host (required)
        - port: Database port (default: 5432)
        - database: Database name (required)
        - user: Database user (required)
        - password: Database password (required)
        - connection_string: Full connection string (alternative to individual params)
        - query_timeout: Query timeout in seconds (default: 30)
        - max_result_rows: Maximum rows to return (default: 10000)
        - read_only: Enforce read-only mode (default: True)
    
    Attributes:
        _connection: psycopg2 connection object
        _connection_pool: Connection pool for efficient resource management
    """
    
    # SQL commands that modify data (for read-only enforcement)
    WRITE_COMMANDS = {
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'TRUNCATE', 'REPLACE', 'MERGE', 'GRANT', 'REVOKE'
    }
    
    def __init__(self, config: DataSourceConfig):
        """Initialize PostgreSQL connector
        
        Args:
            config: Data source configuration
        """
        super().__init__(config)
        
        if psycopg2 is None:
            raise ImportError(
                "psycopg2 is required for PostgreSQL connector. "
                "Install it with: pip install psycopg2-binary"
            )
        
        self._connection_pool: Optional[pool.SimpleConnectionPool] = None
        self._query_timeout = self.config.config.get('query_timeout', 30)
        self._max_result_rows = self.config.config.get('max_result_rows', 10000)
        self._read_only = self.config.config.get('read_only', True)
    
    def _get_connection_params(self) -> Dict[str, Any]:
        """Extract connection parameters from config
        
        Returns:
            Dictionary of connection parameters for psycopg2
        """
        # Check if connection_string is provided
        connection_string = self.config.config.get('connection_string')
        if connection_string:
            return {'dsn': connection_string}
        
        # Build from individual parameters
        params = {}
        
        # Required parameters
        for key in ['host', 'database', 'user', 'password']:
            value = self.config.config.get(key)
            if not value:
                raise DSConnectionError(f"'{key}' is required in configuration")
            params[key] = value
        
        # Optional parameters
        params['port'] = self.config.config.get('port', 5432)
        
        # Connection timeout
        params['connect_timeout'] = self.config.config.get('connect_timeout', 10)
        
        return params
    
    async def connect(self) -> bool:
        """Establish connection to PostgreSQL database
        
        Returns:
            True if connection successful
            
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        try:
            # Get connection parameters
            conn_params = self._get_connection_params()
            
            # Create connection pool (min 1, max 5 connections)
            self._connection_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=5,
                **conn_params
            )
            
            # Test connection by getting one from pool
            test_conn = self._connection_pool.getconn()
            
            # Set read-only mode if configured
            if self._read_only:
                test_conn.set_session(readonly=True)
            
            # Test with a simple query
            cursor = test_conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            cursor.close()
            
            # Return connection to pool
            self._connection_pool.putconn(test_conn)
            
            self._connection = self._connection_pool
            logger.info(f"Successfully connected to PostgreSQL database: {version[0]}")
            return True
            
        except psycopg2.OperationalError as e:
            logger.error(f"Connection failed: {str(e)}")
            raise AuthenticationError(
                f"Failed to connect to PostgreSQL: {str(e)}"
            ) from e
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error: {str(e)}")
            raise DSConnectionError(
                f"PostgreSQL connection error: {str(e)}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during connection: {str(e)}")
            raise DSConnectionError(
                f"Unexpected error connecting to PostgreSQL: {str(e)}"
            ) from e
    
    async def disconnect(self) -> None:
        """Close connection to PostgreSQL database
        
        Closes all connections in the pool and cleans up resources.
        """
        if self._connection_pool:
            try:
                self._connection_pool.closeall()
                logger.info("Closed all PostgreSQL connections")
            except Exception as e:
                logger.warning(f"Error closing connection pool: {str(e)}")
        
        self._connection_pool = None
        self._connection = None
    
    async def test_connection(self) -> bool:
        """Test if the connection is valid
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Try to connect if not already connected
            if not self.is_connected():
                await self.connect()
            
            # Test by executing a simple query
            if self._connection_pool:
                conn = self._connection_pool.getconn()
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1;")
                    cursor.fetchone()
                    cursor.close()
                    return True
                finally:
                    self._connection_pool.putconn(conn)
            
            return False
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def _is_write_query(self, query: str) -> bool:
        """Check if a query contains write operations
        
        Args:
            query: SQL query to check
            
        Returns:
            True if query contains write operations
        """
        # Remove comments and normalize whitespace
        query_upper = re.sub(r'--.*$', '', query, flags=re.MULTILINE).upper()
        query_upper = re.sub(r'/\*.*?\*/', '', query_upper, flags=re.DOTALL)
        
        # Check for write commands
        for command in self.WRITE_COMMANDS:
            if re.search(r'\b' + command + r'\b', query_upper):
                return True
        
        return False
    
    async def list_items(self, path: Optional[str] = None) -> List[DataItem]:
        """List tables and views in the database
        
        Args:
            path: Optional schema name to filter tables (default: 'public')
            
        Returns:
            List of DataItem objects representing tables and views
            
        Raises:
            DataFetchError: If listing fails
        """
        if not self.is_connected():
            raise DataFetchError("Not connected to PostgreSQL database")
        
        try:
            schema = path or 'public'
            
            conn = self._connection_pool.getconn()
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Query to get tables and views with metadata
                query = """
                    SELECT 
                        table_name,
                        table_type,
                        table_schema
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    ORDER BY table_name;
                """
                
                cursor.execute(query, (schema,))
                results = cursor.fetchall()
                
                items = []
                for row in results:
                    # Get row count for tables
                    row_count = 0
                    if row['table_type'] == 'BASE TABLE':
                        try:
                            count_query = sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                                sql.Identifier(schema),
                                sql.Identifier(row['table_name'])
                            )
                            cursor.execute(count_query)
                            row_count = cursor.fetchone()['count']
                        except Exception as e:
                            logger.warning(f"Could not get row count for {row['table_name']}: {e}")
                    
                    item = DataItem(
                        name=row['table_name'],
                        path=f"{schema}.{row['table_name']}",
                        size=row_count,  # Use row count as "size"
                        modified_at=int(datetime.now().timestamp()),
                        metadata={
                            'table_type': row['table_type'],
                            'schema': row['table_schema'],
                        }
                    )
                    items.append(item)
                
                cursor.close()
                logger.info(f"Listed {len(items)} tables/views from schema '{schema}'")
                return items
                
            finally:
                self._connection_pool.putconn(conn)
                
        except psycopg2.Error as e:
            logger.error(f"Failed to list tables: {str(e)}")
            raise DataFetchError(f"Failed to list tables: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error listing tables: {str(e)}")
            raise DataFetchError(f"Unexpected error listing tables: {str(e)}") from e
    
    async def fetch_data(
        self, 
        identifier: str, 
        workspace: str
    ) -> str:
        """Execute SQL query and save results to workspace as CSV
        
        Args:
            identifier: SQL query to execute
            workspace: Local workspace directory path
            
        Returns:
            Local file path where the results were saved
            
        Raises:
            DataFetchError: If query execution or saving fails
        """
        if not self.is_connected():
            raise DataFetchError("Not connected to PostgreSQL database")
        
        # Check for write operations if read-only mode is enabled
        if self._read_only and self._is_write_query(identifier):
            raise DataFetchError(
                "Write operations are not allowed in read-only mode. "
                "Query contains: INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, or similar commands."
            )
        
        try:
            conn = self._connection_pool.getconn()
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Set statement timeout
                cursor.execute(f"SET statement_timeout = {self._query_timeout * 1000};")
                
                # Execute query
                cursor.execute(identifier)
                
                # Fetch results with row limit
                results = cursor.fetchmany(self._max_result_rows)
                
                # Check if there are more rows
                has_more = cursor.fetchone() is not None
                if has_more:
                    logger.warning(
                        f"Query returned more than {self._max_result_rows} rows. "
                        "Results truncated."
                    )
                
                cursor.close()
                
                # Ensure workspace directory exists
                os.makedirs(workspace, exist_ok=True)
                
                # Generate filename based on query hash
                import hashlib
                query_hash = hashlib.md5(identifier.encode()).hexdigest()[:8]
                filename = f"query_result_{query_hash}.csv"
                local_path = os.path.join(workspace, filename)
                
                # Write results to CSV
                if results:
                    with open(local_path, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=results[0].keys())
                        writer.writeheader()
                        writer.writerows(results)
                    
                    logger.info(
                        f"Executed query and saved {len(results)} rows to '{local_path}'"
                    )
                else:
                    # Create empty CSV with no data
                    with open(local_path, 'w', newline='', encoding='utf-8') as csvfile:
                        csvfile.write("")
                    
                    logger.info(f"Query returned no results. Created empty file at '{local_path}'")
                
                return local_path
                
            finally:
                self._connection_pool.putconn(conn)
                
        except psycopg2.errors.QueryCanceled as e:
            logger.error(f"Query timeout after {self._query_timeout} seconds")
            raise DataFetchError(
                f"Query timeout after {self._query_timeout} seconds: {str(e)}"
            ) from e
        except psycopg2.Error as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise DataFetchError(
                f"Query execution failed: {str(e)}"
            ) from e
        except OSError as e:
            logger.error(f"Failed to write results to workspace: {str(e)}")
            raise DataFetchError(
                f"Failed to write results to workspace: {str(e)}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error executing query: {str(e)}")
            raise DataFetchError(
                f"Unexpected error executing query: {str(e)}"
            ) from e
    
    async def get_metadata(self, identifier: str) -> Dict[str, Any]:
        """Get schema information for a table
        
        Args:
            identifier: Table name (can include schema: 'schema.table')
            
        Returns:
            Dictionary containing table schema metadata
            
        Raises:
            DataFetchError: If metadata retrieval fails
        """
        if not self.is_connected():
            raise DataFetchError("Not connected to PostgreSQL database")
        
        try:
            # Parse schema and table name
            parts = identifier.split('.')
            if len(parts) == 2:
                schema, table = parts
            else:
                schema = 'public'
                table = identifier
            
            conn = self._connection_pool.getconn()
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Get column information
                column_query = """
                    SELECT 
                        column_name,
                        data_type,
                        character_maximum_length,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position;
                """
                
                cursor.execute(column_query, (schema, table))
                columns = cursor.fetchall()
                
                if not columns:
                    raise DataFetchError(f"Table '{identifier}' not found")
                
                # Get row count
                count_query = sql.SQL("SELECT COUNT(*) as count FROM {}.{}").format(
                    sql.Identifier(schema),
                    sql.Identifier(table)
                )
                cursor.execute(count_query)
                row_count = cursor.fetchone()['count']
                
                # Get primary key information
                pk_query = """
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid
                        AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = %s::regclass
                        AND i.indisprimary;
                """
                
                cursor.execute(pk_query, (f"{schema}.{table}",))
                primary_keys = [row['attname'] for row in cursor.fetchall()]
                
                cursor.close()
                
                metadata = {
                    'table_name': table,
                    'schema': schema,
                    'row_count': row_count,
                    'columns': [dict(col) for col in columns],
                    'primary_keys': primary_keys,
                }
                
                logger.info(f"Retrieved metadata for table: {identifier}")
                return metadata
                
            finally:
                self._connection_pool.putconn(conn)
                
        except psycopg2.Error as e:
            logger.error(f"Failed to get metadata for '{identifier}': {str(e)}")
            raise DataFetchError(
                f"Failed to get metadata for '{identifier}': {str(e)}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error getting metadata: {str(e)}")
            raise DataFetchError(
                f"Unexpected error getting metadata for '{identifier}': {str(e)}"
            ) from e
    
    async def get_table_preview(
        self,
        table_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get preview of table data
        
        This is an additional method specific to PostgreSQL for previewing table contents.
        
        Args:
            table_name: Name of table to preview (can include schema: 'schema.table')
            limit: Number of rows to return (default: 10)
            
        Returns:
            List of dictionaries representing rows
            
        Raises:
            DataFetchError: If preview fails
        """
        if not self.is_connected():
            raise DataFetchError("Not connected to PostgreSQL database")
        
        try:
            # Parse schema and table name
            parts = table_name.split('.')
            if len(parts) == 2:
                schema, table = parts
            else:
                schema = 'public'
                table = table_name
            
            conn = self._connection_pool.getconn()
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Query to get preview
                query = sql.SQL("SELECT * FROM {}.{} LIMIT %s").format(
                    sql.Identifier(schema),
                    sql.Identifier(table)
                )
                
                cursor.execute(query, (limit,))
                results = cursor.fetchall()
                
                cursor.close()
                
                logger.info(f"Retrieved {len(results)} preview rows from '{table_name}'")
                return [dict(row) for row in results]
                
            finally:
                self._connection_pool.putconn(conn)
                
        except psycopg2.Error as e:
            logger.error(f"Failed to preview table '{table_name}': {str(e)}")
            raise DataFetchError(
                f"Failed to preview table '{table_name}': {str(e)}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error previewing table: {str(e)}")
            raise DataFetchError(
                f"Unexpected error previewing table '{table_name}': {str(e)}"
            ) from e
