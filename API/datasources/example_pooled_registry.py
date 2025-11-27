"""
Example: Integrating Connection Pooling with Data Source Registry

This example shows how to extend the DataSourceRegistry to use connection pooling
for efficient resource management.
"""

import asyncio
from typing import Optional

from .registry import DataSourceRegistry
from .pool import ConnectionPoolManager, PoolConfig
from .base import DataSourceConnector
from .credentials import CredentialManager


class PooledDataSourceRegistry(DataSourceRegistry):
    """Extended registry with connection pooling support
    
    This class extends the base DataSourceRegistry to use connection pooling
    for all data source connectors, providing better resource management and
    performance for high-concurrency scenarios.
    """
    
    def __init__(
        self,
        credential_manager: Optional[CredentialManager] = None,
        pool_config: Optional[PoolConfig] = None,
        cache_ttl: int = 300
    ):
        """Initialize pooled registry
        
        Args:
            credential_manager: Manager for credential encryption
            pool_config: Default configuration for connection pools
            cache_ttl: Time-to-live for metadata cache in seconds
        """
        super().__init__(credential_manager, cache_ttl)
        self._pool_manager = ConnectionPoolManager(default_config=pool_config)
    
    async def get_connector(self, data_source_id: str) -> DataSourceConnector:
        """Get a connector from the connection pool
        
        This overrides the base implementation to use connection pooling.
        Connectors are acquired from a pool and should be released back
        using release_connector() when done.
        
        Args:
            data_source_id: ID of the data source
        
        Returns:
            Connected DataSourceConnector instance from pool
        
        Raises:
            RegistryError: If data source ID does not exist
            PoolError: If unable to acquire connection from pool
        """
        if data_source_id not in self._configs:
            from .registry import RegistryError
            raise RegistryError(
                f"Data source with ID '{data_source_id}' not found"
            )
        
        # Create connector factory
        def factory():
            config = self._configs[data_source_id]
            return self._create_connector(config)
        
        # Get pool and acquire connection
        pool = await self._pool_manager.get_pool(
            data_source_id,
            factory
        )
        
        return await pool.acquire()
    
    async def release_connector(
        self,
        data_source_id: str,
        connector: DataSourceConnector
    ) -> None:
        """Release a connector back to the pool
        
        This should be called when done using a connector obtained from
        get_connector(). The connector will be returned to the pool for reuse.
        
        Args:
            data_source_id: ID of the data source
            connector: The connector to release
        """
        if data_source_id in self._pool_manager._pools:
            pool = self._pool_manager._pools[data_source_id]
            await pool.release(connector)
    
    async def unregister_data_source(self, data_source_id: str) -> None:
        """Unregister data source and close its connection pool
        
        This extends the base implementation to also close the connection pool
        for the data source.
        
        Args:
            data_source_id: ID of the data source to remove
        """
        # Close the pool first
        await self._pool_manager.close_pool(data_source_id)
        
        # Then unregister from base registry
        await super().unregister_data_source(data_source_id)
    
    async def disconnect_all(self) -> None:
        """Disconnect all connectors and close all pools
        
        This extends the base implementation to also close all connection pools.
        Should be called during application shutdown.
        """
        # Close all pools
        await self._pool_manager.close_all()
        
        # Then disconnect any remaining connectors
        await super().disconnect_all()
    
    def get_pool_stats(self, data_source_id: str) -> Optional[dict]:
        """Get connection pool statistics for a data source
        
        Args:
            data_source_id: ID of the data source
        
        Returns:
            Dictionary with pool statistics or None if no pool exists
        """
        return self._pool_manager.get_pool_stats(data_source_id)
    
    def list_active_pools(self) -> list[str]:
        """List all data sources with active connection pools
        
        Returns:
            List of data source IDs with active pools
        """
        return self._pool_manager.list_pools()


# Example usage
async def example_usage():
    """Example of using PooledDataSourceRegistry"""
    
    # Create pooled registry with custom pool configuration
    pool_config = PoolConfig(
        max_size=10,      # Maximum 10 connections per data source
        min_size=2,       # Keep at least 2 connections warm
        max_idle_time=300,  # Close connections idle for 5 minutes
        acquire_timeout=30,  # Wait up to 30 seconds for a connection
        max_lifetime=3600   # Recreate connections after 1 hour
    )
    
    registry = PooledDataSourceRegistry(pool_config=pool_config)
    
    # Register a connector class (example with mock connector)
    from .base import DataSourceType, DataSourceConfig
    
    # Assume we have a PostgreSQL connector
    # registry.register_connector_class(DataSourceType.POSTGRESQL, PostgreSQLConnector)
    
    # Register a data source
    config = DataSourceConfig(
        id="production-db",
        type=DataSourceType.POSTGRESQL,
        name="Production Database",
        config={
            "host": "db.example.com",
            "port": 5432,
            "database": "myapp",
            "user": "readonly",
            "password": "secret"
        }
    )
    
    # await registry.register_data_source(config)
    
    # Use the connector with automatic pooling
    # connector = await registry.get_connector("production-db")
    # try:
    #     # Use connector
    #     data = await connector.fetch_data("SELECT * FROM users", "/workspace")
    #     print(f"Fetched data to: {data}")
    # finally:
    #     # Always release back to pool
    #     await registry.release_connector("production-db", connector)
    
    # Check pool statistics
    # stats = registry.get_pool_stats("production-db")
    # if stats:
    #     print(f"Pool stats: {stats['in_use']}/{stats['total']} connections in use")
    
    # List active pools
    # active_pools = registry.list_active_pools()
    # print(f"Active pools: {active_pools}")
    
    # Cleanup
    await registry.disconnect_all()


# Context manager for automatic connector release
class PooledConnectorContext:
    """Context manager for automatic connector acquisition and release"""
    
    def __init__(self, registry: PooledDataSourceRegistry, data_source_id: str):
        self.registry = registry
        self.data_source_id = data_source_id
        self.connector = None
    
    async def __aenter__(self):
        self.connector = await self.registry.get_connector(self.data_source_id)
        return self.connector
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.connector:
            await self.registry.release_connector(self.data_source_id, self.connector)


async def example_with_context_manager():
    """Example using context manager for automatic release"""
    
    registry = PooledDataSourceRegistry()
    
    # Use context manager for automatic release
    async with PooledConnectorContext(registry, "production-db") as connector:
        # Connector is automatically acquired
        data = await connector.fetch_data("query", "/workspace")
        print(f"Data: {data}")
        # Connector is automatically released when exiting context


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
