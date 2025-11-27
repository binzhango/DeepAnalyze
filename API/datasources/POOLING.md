# Connection Pooling

This document describes the connection pooling implementation for data source connectors.

## Overview

Connection pooling provides efficient resource management for data source connections by:
- Reusing connections across multiple requests
- Limiting concurrent connections to prevent resource exhaustion
- Automatically cleaning up idle and expired connections
- Managing connection lifecycle (creation, health checking, disposal)

## Architecture

### Components

1. **PooledConnection**: Wrapper around a data source connector with metadata
   - Tracks creation time, last used time, usage count
   - Provides expiration and idle time checking
   - Maintains in-use status

2. **ConnectionPool**: Manages connections for a single data source
   - Creates and maintains a pool of connections
   - Handles connection acquisition and release
   - Performs automatic cleanup of stale connections
   - Enforces pool size limits

3. **ConnectionPoolManager**: Manages pools for multiple data sources
   - Creates pools on-demand
   - Provides centralized pool management
   - Tracks pool statistics

### Configuration

Connection pools are configured using `PoolConfig`:

```python
from API.datasources import PoolConfig

config = PoolConfig(
    max_size=10,          # Maximum connections in pool
    min_size=1,           # Minimum connections to maintain
    max_idle_time=300,    # Max idle time (seconds) before cleanup
    acquire_timeout=30,   # Max time to wait for connection
    max_lifetime=3600     # Max connection lifetime (seconds)
)
```

## Usage

### Basic Usage with ConnectionPool

```python
from API.datasources import ConnectionPool, PoolConfig

# Create a connector factory
def connector_factory():
    return MyConnector(config)

# Create pool
pool = ConnectionPool(
    data_source_id="my-datasource",
    connector_factory=connector_factory,
    config=PoolConfig(max_size=5)
)

# Initialize pool
await pool.initialize()

# Acquire connection
connector = await pool.acquire()

try:
    # Use connector
    data = await connector.fetch_data("query", "/workspace")
finally:
    # Always release connection back to pool
    await pool.release(connector)

# Close pool when done
await pool.close()
```

### Using ConnectionPoolManager

```python
from API.datasources import ConnectionPoolManager, PoolConfig

# Create manager
manager = ConnectionPoolManager(
    default_config=PoolConfig(max_size=10)
)

# Get pool for a data source (creates if doesn't exist)
pool = await manager.get_pool(
    data_source_id="my-datasource",
    connector_factory=connector_factory
)

# Acquire and use connection
connector = await pool.acquire()
try:
    # Use connector
    pass
finally:
    await pool.release(connector)

# Get pool statistics
stats = manager.get_pool_stats("my-datasource")
print(f"Total: {stats['total']}, In use: {stats['in_use']}")

# Close specific pool
await manager.close_pool("my-datasource")

# Or close all pools
await manager.close_all()
```

### Integration with DataSourceRegistry

The registry can be enhanced to use connection pooling:

```python
from API.datasources import DataSourceRegistry, ConnectionPoolManager

class PooledDataSourceRegistry(DataSourceRegistry):
    def __init__(self, pool_manager=None, **kwargs):
        super().__init__(**kwargs)
        self._pool_manager = pool_manager or ConnectionPoolManager()
    
    async def get_connector(self, data_source_id: str):
        """Get connector from pool instead of creating new one"""
        config = self.get_config(data_source_id, decrypt=True)
        
        def factory():
            return self._create_connector(config)
        
        pool = await self._pool_manager.get_pool(
            data_source_id,
            factory
        )
        
        return await pool.acquire()
    
    async def release_connector(self, data_source_id: str, connector):
        """Release connector back to pool"""
        if data_source_id in self._pool_manager._pools:
            pool = self._pool_manager._pools[data_source_id]
            await pool.release(connector)
```

## Features

### Connection Reuse

Connections are automatically reused when released back to the pool:

```python
# First request
conn1 = await pool.acquire()
await pool.release(conn1)

# Second request gets same connection
conn2 = await pool.acquire()
assert conn1 is conn2  # Same connection object
```

### Concurrent Connection Limiting

Pool enforces maximum connection limit:

```python
config = PoolConfig(max_size=2)
pool = ConnectionPool("ds", factory, config)

conn1 = await pool.acquire()  # OK
conn2 = await pool.acquire()  # OK
conn3 = await pool.acquire(timeout=1)  # Raises PoolError after timeout
```

### Automatic Cleanup

Pool automatically cleans up:
- **Expired connections**: Connections exceeding `max_lifetime`
- **Idle connections**: Connections idle longer than `max_idle_time`
- **Unhealthy connections**: Connections failing health checks

Cleanup runs automatically in the background every 60 seconds.

### Health Checking

Connections are health-checked when released:

```python
connector = await pool.acquire()

# If connector becomes unhealthy
connector.should_fail = True

# Release will detect and remove unhealthy connection
await pool.release(connector)
```

### Pool Statistics

Monitor pool health and usage:

```python
stats = manager.get_pool_stats("my-datasource")
# Returns:
# {
#     "total": 5,        # Total connections
#     "available": 3,    # Available connections
#     "in_use": 2,       # Connections in use
#     "max_size": 10,    # Maximum pool size
#     "min_size": 1      # Minimum pool size
# }
```

## Best Practices

### 1. Always Release Connections

Use try/finally to ensure connections are released:

```python
connector = await pool.acquire()
try:
    # Use connector
    result = await connector.fetch_data(...)
finally:
    await pool.release(connector)
```

### 2. Configure Pool Sizes Appropriately

- **max_size**: Based on expected concurrent requests and backend limits
- **min_size**: Keep at least 1 to avoid cold start delays
- **max_idle_time**: Balance between keeping connections warm and resource usage
- **max_lifetime**: Prevent connection leaks and stale connections

### 3. Monitor Pool Statistics

Regularly check pool statistics to:
- Detect connection leaks (high in_use count)
- Optimize pool sizes (frequent timeouts = increase max_size)
- Identify performance issues

### 4. Handle Pool Errors

```python
from API.datasources import PoolError

try:
    connector = await pool.acquire(timeout=5)
except PoolError as e:
    # Handle timeout or pool closed errors
    logger.error(f"Failed to acquire connection: {e}")
```

### 5. Clean Shutdown

Always close pools during application shutdown:

```python
# In application shutdown handler
await manager.close_all()
```

## Performance Considerations

### Connection Creation Overhead

- First request to a pool may be slower (connection creation)
- Subsequent requests reuse connections (faster)
- Configure `min_size` to pre-create connections

### Memory Usage

- Each connection consumes memory
- Balance `max_size` with available memory
- Idle connections are cleaned up automatically

### Concurrency

- Pool uses asyncio locks for thread safety
- Lock contention is minimal for typical workloads
- Consider multiple pools for high-concurrency scenarios

## Troubleshooting

### Timeout Errors

**Problem**: `PoolError: Timeout waiting for connection`

**Solutions**:
- Increase `max_size` in pool config
- Increase `acquire_timeout`
- Check for connection leaks (not releasing connections)
- Verify backend can handle more connections

### Connection Leaks

**Problem**: Pool exhausted, connections not released

**Solutions**:
- Always use try/finally to release connections
- Check for exceptions preventing release
- Monitor `in_use` count in statistics

### Stale Connections

**Problem**: Connections become invalid over time

**Solutions**:
- Reduce `max_lifetime` to force recreation
- Ensure `test_connection()` is implemented correctly
- Check backend connection timeout settings

## Testing

The connection pooling implementation includes comprehensive tests:

```bash
# Run all pool tests
pytest API/datasources/test_pool.py -v

# Run specific test
pytest API/datasources/test_pool.py::TestConnectionPool::test_acquire_connection -v
```

Test coverage includes:
- Pool initialization and configuration
- Connection acquisition and release
- Concurrent access
- Cleanup of expired/idle connections
- Error handling
- Pool statistics
- Manager functionality

## Future Enhancements

Potential improvements:
- Connection warming (pre-create connections)
- Adaptive pool sizing based on load
- Connection validation on acquire
- Metrics and monitoring integration
- Per-tenant pool isolation
- Connection priority queuing
