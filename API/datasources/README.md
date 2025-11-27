# Data Sources Module

This module provides a plugin-based architecture for integrating external data sources with the DeepAnalyze API.

## Components

### 1. Base Connector (`base.py`)
Defines the abstract interface that all data source connectors must implement.

**Key Classes:**
- `DataSourceConnector`: Abstract base class for all connectors
- `DataSourceConfig`: Configuration for a data source
- `DataItem`: Represents an item in a data source
- `DataSourceType`: Enum of supported data source types

### 2. Credential Manager (`credentials.py`)
Handles secure encryption and decryption of sensitive credentials.

**Key Features:**
- Fernet symmetric encryption
- Automatic key generation or environment variable loading
- Credential sanitization for safe logging

### 3. Data Source Registry (`registry.py`)
Central registry for managing data source connectors and their lifecycle.

**Key Features:**
- Connector factory pattern
- Connection lifecycle management
- Metadata caching
- Thread-safe operations
- Credential encryption/decryption

### 4. Connection Pooling (`pool.py`)
Provides efficient connection pooling and resource management for data sources.

**Key Classes:**
- `ConnectionPool`: Manages connections for a single data source
- `ConnectionPoolManager`: Manages pools for multiple data sources
- `PoolConfig`: Configuration for connection pools
- `PooledConnection`: Wrapper for pooled connections

**Key Features:**
- Connection reuse across requests
- Concurrent connection limiting
- Automatic cleanup of idle/expired connections
- Health checking
- Pool statistics and monitoring

See [POOLING.md](./POOLING.md) for detailed documentation.

## Usage Examples

### Basic Setup

```python
from API.datasources import (
    DataSourceRegistry,
    DataSourceConfig,
    DataSourceType,
    CredentialManager
)

# Initialize credential manager
credential_manager = CredentialManager()

# Create registry
registry = DataSourceRegistry(credential_manager=credential_manager)

# Register a connector class (e.g., Azure Blob)
from API.datasources.azure_blob import AzureBlobConnector
registry.register_connector_class(DataSourceType.AZURE_BLOB, AzureBlobConnector)
```

### Register a Data Source

```python
# Create configuration
config = DataSourceConfig(
    id="my-azure-storage",
    type=DataSourceType.AZURE_BLOB,
    name="Production Azure Storage",
    config={
        "connection_string": "DefaultEndpointsProtocol=https;...",
        "container": "data-files"
    },
    metadata={
        "environment": "production",
        "owner": "data-team"
    }
)

# Register with connection test
await registry.register_data_source(config, test_connection=True)
```

### Use a Data Source

```python
# Get a connector
connector = await registry.get_connector("my-azure-storage")

# List available items
items = await connector.list_items()
for item in items:
    print(f"{item.name}: {item.size} bytes")

# Fetch data to workspace
local_path = await connector.fetch_data(
    identifier="data/sales.csv",
    workspace="/tmp/workspace"
)
print(f"Downloaded to: {local_path}")
```

### Manage Data Sources

```python
# List all data sources (sanitized)
data_sources = registry.list_data_sources()
for ds in data_sources:
    print(f"{ds.name} ({ds.type.value})")

# Get configuration (sanitized)
config = registry.get_config("my-azure-storage", sanitize=True)
print(config.config)  # Sensitive fields are redacted

# Test connection
is_connected = await registry.test_connection("my-azure-storage")
print(f"Connection status: {is_connected}")

# Unregister data source
await registry.unregister_data_source("my-azure-storage")
```

### Metadata Caching

```python
# Cache metadata
metadata = {"tables": ["users", "orders", "products"]}
registry.cache_metadata("my-database", metadata)

# Retrieve cached metadata
cached = registry.get_cached_metadata("my-database")
if cached:
    print("Using cached metadata")
else:
    print("Cache expired or not found")

# Clear cache
registry.clear_cache("my-database")  # Clear specific
registry.clear_cache()  # Clear all
```

### Cleanup

```python
# Disconnect all connectors (e.g., during shutdown)
await registry.disconnect_all()
```

## Implementing a Custom Connector

To add support for a new data source type:

1. Create a new connector class that inherits from `DataSourceConnector`
2. Implement all abstract methods
3. Register the connector class with the registry

```python
from API.datasources import DataSourceConnector, DataSourceConfig, DataItem
from typing import List, Dict, Any, Optional

class MyCustomConnector(DataSourceConnector):
    async def connect(self) -> bool:
        # Establish connection
        self._connection = create_connection(self.config.config)
        return True
    
    async def disconnect(self) -> None:
        # Close connection
        if self._connection:
            self._connection.close()
            self._connection = None
    
    async def test_connection(self) -> bool:
        # Test if connection works
        try:
            await self.connect()
            # Perform simple test operation
            return True
        except Exception:
            return False
        finally:
            await self.disconnect()
    
    async def list_items(self, path: Optional[str] = None) -> List[DataItem]:
        # List available items
        items = []
        # ... implementation
        return items
    
    async def fetch_data(self, identifier: str, workspace: str) -> str:
        # Fetch data and save to workspace
        local_path = os.path.join(workspace, "data.csv")
        # ... implementation
        return local_path
    
    async def get_metadata(self, identifier: str) -> Dict[str, Any]:
        # Get metadata for item
        metadata = {}
        # ... implementation
        return metadata

# Register the connector
registry.register_connector_class(DataSourceType.CUSTOM, MyCustomConnector)
```

## Security Considerations

1. **Credential Encryption**: All credentials are encrypted at rest using Fernet symmetric encryption
2. **Sanitization**: Use `sanitize=True` when returning configs to clients to prevent credential exposure
3. **Logging**: Credentials are never logged; use the credential manager's sanitization features
4. **Environment Variables**: Store encryption keys in environment variables, not in code
5. **Connection Pooling**: The registry manages connection lifecycle to prevent resource leaks

## Testing

### Unit Tests

Unit tests use mocks to test individual components in isolation.

Run all unit tests:
```bash
pytest API/datasources/ -v -k "not integration"
```

Run specific test file:
```bash
pytest API/datasources/test_registry.py -v
pytest API/datasources/test_azure_blob.py -v
```

### Integration Tests

Integration tests validate connectors against real services (Azure Blob Storage or Azurite emulator).

**Quick Start:**
```bash
# Automatic setup and run
./API/datasources/run_integration_tests.sh --auto-start

# Or manually start Azurite first
docker run -p 10000:10000 mcr.microsoft.com/azure-storage/azurite azurite-blob --blobHost 0.0.0.0

# Then run tests
pytest API/datasources/test_azure_blob_integration.py -v
```

**See [INTEGRATION_TESTS.md](./INTEGRATION_TESTS.md) for complete documentation.**

### Test Coverage

Current test coverage:
- **Base connector**: 87 unit tests passing ✅
- **Credential manager**: Full coverage ✅
- **Registry**: Full coverage ✅
- **Connection pooling**: Full coverage ✅
- **Azure Blob connector**: Unit tests ✅ + Integration tests ✅

## Architecture

```
┌─────────────────────────────────────────┐
│      Application / API Layer            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Data Source Registry               │
│  - Connector Management                 │
│  - Lifecycle Control                    │
│  - Metadata Caching                     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Credential Manager                 │
│  - Encryption/Decryption                │
│  - Sanitization                         │
└─────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Data Source Connectors             │
│  ┌──────────┐  ┌──────────┐            │
│  │  Azure   │  │PostgreSQL│            │
│  │  Blob    │  │          │            │
│  └──────────┘  └──────────┘            │
└─────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      External Data Sources              │
│  - Azure Blob Storage                   │
│  - PostgreSQL Databases                 │
│  - Other Sources                        │
└─────────────────────────────────────────┘
```

## Connection Pooling

Connection pooling is now available for efficient resource management. See [POOLING.md](./POOLING.md) for complete documentation.

**Quick Example:**

```python
from API.datasources import ConnectionPoolManager, PoolConfig

# Create pool manager
manager = ConnectionPoolManager(
    default_config=PoolConfig(max_size=10, min_size=2)
)

# Get pool for a data source
pool = await manager.get_pool(
    data_source_id="my-database",
    connector_factory=lambda: MyConnector(config)
)

# Acquire connection
connector = await pool.acquire()
try:
    # Use connector
    data = await connector.fetch_data("query", "/workspace")
finally:
    # Always release
    await pool.release(connector)

# Get statistics
stats = manager.get_pool_stats("my-database")
print(f"Pool: {stats['in_use']}/{stats['total']} connections in use")
```

## Next Steps

1. Implement Azure Blob Storage connector (`azure_blob.py`)
2. Implement PostgreSQL connector (`postgresql.py`) with connection pooling
3. Create API endpoints for data source management
4. Integrate with chat API for automatic data fetching
5. Integrate connection pooling with registry
