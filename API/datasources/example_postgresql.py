"""
Example usage of PostgreSQL connector
Demonstrates how to connect to PostgreSQL databases and query data
"""

import asyncio
import os
import tempfile
from API.datasources.postgresql import PostgreSQLConnector
from API.datasources.base import DataSourceConfig, DataSourceType
from API.datasources.registry import DataSourceRegistry


async def example_basic_connection():
    """Example: Basic connection to PostgreSQL"""
    print("\n" + "="*70)
    print("Example 1: Basic PostgreSQL Connection")
    print("="*70)
    
    # Create configuration
    config = DataSourceConfig(
        id="example-pg",
        type=DataSourceType.POSTGRESQL,
        name="Example PostgreSQL Database",
        config={
            'host': 'localhost',
            'port': 5432,
            'database': 'mydb',
            'user': 'myuser',
            'password': 'mypassword',
            'read_only': True,  # Enforce read-only mode
        }
    )
    
    # Create connector
    connector = PostgreSQLConnector(config)
    
    try:
        # Connect
        print("Connecting to PostgreSQL...")
        await connector.connect()
        print("✓ Connected successfully")
        
        # Test connection
        is_valid = await connector.test_connection()
        print(f"✓ Connection test: {'PASSED' if is_valid else 'FAILED'}")
        
    finally:
        await connector.disconnect()
        print("✓ Disconnected")


async def example_connection_string():
    """Example: Connection using connection string"""
    print("\n" + "="*70)
    print("Example 2: Connection with Connection String")
    print("="*70)
    
    config = DataSourceConfig(
        id="example-pg-connstr",
        type=DataSourceType.POSTGRESQL,
        name="PostgreSQL with Connection String",
        config={
            'connection_string': 'postgresql://user:password@localhost:5432/mydb',
            'read_only': True,
        }
    )
    
    connector = PostgreSQLConnector(config)
    
    try:
        print("Connecting with connection string...")
        await connector.connect()
        print("✓ Connected successfully")
    finally:
        await connector.disconnect()


async def example_list_tables():
    """Example: List tables in database"""
    print("\n" + "="*70)
    print("Example 3: List Tables")
    print("="*70)
    
    config = DataSourceConfig(
        id="example-pg",
        type=DataSourceType.POSTGRESQL,
        name="Example PostgreSQL",
        config={
            'host': 'localhost',
            'port': 5432,
            'database': 'mydb',
            'user': 'myuser',
            'password': 'mypassword',
        }
    )
    
    connector = PostgreSQLConnector(config)
    
    try:
        await connector.connect()
        
        # List tables in public schema
        print("Listing tables in 'public' schema...")
        tables = await connector.list_items()
        
        print(f"\nFound {len(tables)} tables:")
        for table in tables:
            print(f"  - {table.name} ({table.size} rows)")
            print(f"    Type: {table.metadata.get('table_type')}")
            print(f"    Schema: {table.metadata.get('schema')}")
        
        # List tables in specific schema
        print("\nListing tables in 'sales' schema...")
        sales_tables = await connector.list_items(path='sales')
        print(f"Found {len(sales_tables)} tables in 'sales' schema")
        
    finally:
        await connector.disconnect()


async def example_execute_query():
    """Example: Execute SQL query and save results"""
    print("\n" + "="*70)
    print("Example 4: Execute Query")
    print("="*70)
    
    config = DataSourceConfig(
        id="example-pg",
        type=DataSourceType.POSTGRESQL,
        name="Example PostgreSQL",
        config={
            'host': 'localhost',
            'port': 5432,
            'database': 'mydb',
            'user': 'myuser',
            'password': 'mypassword',
            'query_timeout': 30,
            'max_result_rows': 1000,
            'read_only': True,
        }
    )
    
    connector = PostgreSQLConnector(config)
    
    try:
        await connector.connect()
        
        # Execute query
        query = """
            SELECT 
                customer_id,
                customer_name,
                total_orders,
                total_spent
            FROM customers
            WHERE total_spent > 1000
            ORDER BY total_spent DESC
            LIMIT 10
        """
        
        with tempfile.TemporaryDirectory() as workspace:
            print("Executing query...")
            result_path = await connector.fetch_data(query, workspace)
            
            print(f"✓ Query executed successfully")
            print(f"✓ Results saved to: {result_path}")
            
            # Read and display results
            import csv
            with open(result_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                print(f"\nRetrieved {len(rows)} rows:")
                for i, row in enumerate(rows[:5], 1):
                    print(f"  {i}. {row}")
        
    finally:
        await connector.disconnect()


async def example_get_table_metadata():
    """Example: Get table schema and metadata"""
    print("\n" + "="*70)
    print("Example 5: Get Table Metadata")
    print("="*70)
    
    config = DataSourceConfig(
        id="example-pg",
        type=DataSourceType.POSTGRESQL,
        name="Example PostgreSQL",
        config={
            'host': 'localhost',
            'port': 5432,
            'database': 'mydb',
            'user': 'myuser',
            'password': 'mypassword',
        }
    )
    
    connector = PostgreSQLConnector(config)
    
    try:
        await connector.connect()
        
        # Get metadata for a table
        print("Getting metadata for 'customers' table...")
        metadata = await connector.get_metadata('customers')
        
        print(f"\nTable: {metadata['table_name']}")
        print(f"Schema: {metadata['schema']}")
        print(f"Row count: {metadata['row_count']}")
        print(f"Primary keys: {metadata['primary_keys']}")
        
        print("\nColumns:")
        for col in metadata['columns']:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            print(f"  - {col['column_name']}: {col['data_type']} {nullable}")
        
        # Get metadata for schema-qualified table
        print("\nGetting metadata for 'sales.orders' table...")
        sales_metadata = await connector.get_metadata('sales.orders')
        print(f"Table: {sales_metadata['schema']}.{sales_metadata['table_name']}")
        print(f"Row count: {sales_metadata['row_count']}")
        
    finally:
        await connector.disconnect()


async def example_table_preview():
    """Example: Preview table data"""
    print("\n" + "="*70)
    print("Example 6: Table Preview")
    print("="*70)
    
    config = DataSourceConfig(
        id="example-pg",
        type=DataSourceType.POSTGRESQL,
        name="Example PostgreSQL",
        config={
            'host': 'localhost',
            'port': 5432,
            'database': 'mydb',
            'user': 'myuser',
            'password': 'mypassword',
        }
    )
    
    connector = PostgreSQLConnector(config)
    
    try:
        await connector.connect()
        
        # Get preview of table
        print("Getting preview of 'customers' table (first 5 rows)...")
        preview = await connector.get_table_preview('customers', limit=5)
        
        print(f"\nPreview ({len(preview)} rows):")
        for i, row in enumerate(preview, 1):
            print(f"  Row {i}: {row}")
        
    finally:
        await connector.disconnect()


async def example_read_only_enforcement():
    """Example: Read-only mode enforcement"""
    print("\n" + "="*70)
    print("Example 7: Read-Only Mode Enforcement")
    print("="*70)
    
    config = DataSourceConfig(
        id="example-pg",
        type=DataSourceType.POSTGRESQL,
        name="Example PostgreSQL",
        config={
            'host': 'localhost',
            'port': 5432,
            'database': 'mydb',
            'user': 'myuser',
            'password': 'mypassword',
            'read_only': True,  # Enforce read-only
        }
    )
    
    connector = PostgreSQLConnector(config)
    
    try:
        await connector.connect()
        
        with tempfile.TemporaryDirectory() as workspace:
            # Try to execute a write query
            print("Attempting to execute DELETE query in read-only mode...")
            try:
                await connector.fetch_data(
                    "DELETE FROM customers WHERE id = 999",
                    workspace
                )
                print("✗ Write query was allowed (should not happen!)")
            except Exception as e:
                print(f"✓ Write query blocked: {str(e)}")
            
            # Try SELECT query (should work)
            print("\nAttempting to execute SELECT query...")
            try:
                result_path = await connector.fetch_data(
                    "SELECT * FROM customers LIMIT 1",
                    workspace
                )
                print(f"✓ SELECT query allowed: {result_path}")
            except Exception as e:
                print(f"✗ SELECT query failed: {str(e)}")
        
    finally:
        await connector.disconnect()


async def example_with_registry():
    """Example: Using PostgreSQL connector with registry"""
    print("\n" + "="*70)
    print("Example 8: Using Registry")
    print("="*70)
    
    # Create registry
    registry = DataSourceRegistry()
    
    # Register PostgreSQL connector class
    registry.register_connector_class(DataSourceType.POSTGRESQL, PostgreSQLConnector)
    
    # Register a data source
    config = DataSourceConfig(
        id="production-db",
        type=DataSourceType.POSTGRESQL,
        name="Production Database",
        config={
            'host': 'prod-db.example.com',
            'port': 5432,
            'database': 'production',
            'user': 'readonly_user',
            'password': 'secure_password',
            'read_only': True,
        }
    )
    
    try:
        print("Registering data source...")
        await registry.register_data_source(config, test_connection=False)
        print("✓ Data source registered")
        
        # List data sources
        print("\nListing data sources...")
        sources = registry.list_data_sources()
        for source in sources:
            print(f"  - {source.id}: {source.name} ({source.type.value})")
            # Note: Sensitive credentials are sanitized
            print(f"    Config: {source.config}")
        
        # Get connector from registry
        print("\nGetting connector from registry...")
        connector = await registry.get_connector("production-db")
        print("✓ Connector retrieved and connected")
        
        # Use connector
        tables = await connector.list_items()
        print(f"✓ Found {len(tables)} tables")
        
    finally:
        # Clean up
        await registry.disconnect_all()
        print("\n✓ All connections closed")


async def example_error_handling():
    """Example: Error handling"""
    print("\n" + "="*70)
    print("Example 9: Error Handling")
    print("="*70)
    
    # Invalid configuration
    config = DataSourceConfig(
        id="invalid-pg",
        type=DataSourceType.POSTGRESQL,
        name="Invalid PostgreSQL",
        config={
            'host': 'nonexistent-host.example.com',
            'port': 5432,
            'database': 'mydb',
            'user': 'myuser',
            'password': 'wrongpassword',
        }
    )
    
    connector = PostgreSQLConnector(config)
    
    try:
        print("Attempting to connect to invalid host...")
        await connector.connect()
        print("✗ Connection succeeded (unexpected)")
    except Exception as e:
        print(f"✓ Connection failed as expected: {type(e).__name__}")
        print(f"  Error: {str(e)}")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("PostgreSQL Connector Examples")
    print("="*70)
    print("\nNote: These examples require a running PostgreSQL instance.")
    print("Update the connection parameters to match your setup.")
    print("="*70)
    
    # Run examples
    examples = [
        ("Basic Connection", example_basic_connection),
        ("Connection String", example_connection_string),
        ("List Tables", example_list_tables),
        ("Execute Query", example_execute_query),
        ("Table Metadata", example_get_table_metadata),
        ("Table Preview", example_table_preview),
        ("Read-Only Enforcement", example_read_only_enforcement),
        ("Using Registry", example_with_registry),
        ("Error Handling", example_error_handling),
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\nTo run an example, uncomment the corresponding line in main()")
    print("or run specific examples individually.")
    
    # Uncomment to run specific examples:
    # asyncio.run(example_basic_connection())
    # asyncio.run(example_connection_string())
    # asyncio.run(example_list_tables())
    # asyncio.run(example_execute_query())
    # asyncio.run(example_get_table_metadata())
    # asyncio.run(example_table_preview())
    # asyncio.run(example_read_only_enforcement())
    # asyncio.run(example_with_registry())
    # asyncio.run(example_error_handling())


if __name__ == '__main__':
    main()
