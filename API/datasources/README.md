# Data Source Connectors

This module provides a plugin-based architecture for integrating external data sources with DeepAnalyze.

## Overview

The data source connector system allows DeepAnalyze to fetch data from various external sources like Azure Blob Storage, PostgreSQL databases, and more. The architecture is designed to be extensible, secure, and performant.

## Architecture

```
DataSourceConnector (Abstract Base Class)
    ├── AzureBlobConnector (Azure Blob Storage)
    ├── PostgreSQLConnector (PostgreSQL Database)
    └── LocalFileConnector (Local File System)
```

## Core Components

### 1. DataSourceType

Enumeration of supported data source types:

```python
class DataSourceType(Enum):
    AZURE_BLOB = "azure_blob"
    POSTGRESQL = "postgresql"
    LOCAL_FILE = "local_file"
```

### 2. DataSourceConfig

Configuration for a data source connection:

```python
@dataclass
class DataSourceConfig:
    id: str                      # Unique identifier
    type: DataSourceType         # Type of data source
    name: str                    # Human-readable name
    config: Dict[str, Any]       # Type-specific configuration
    created_at: int              # Unix timestamp
    metadata: Dict[str, Any]     # Additional metadata
```

**Example:**

```python
config = DataSourceConfig(
    id="ds-azure-prod",
    type=DataSourceType.AZURE_BLOB,
    name="Production Azure Storage",
    config={
        "connection_string": "DefaultEndpointsProtocol=https;...",
        "container_name": "data"
    },
    metadata={"region": "us-east-1", "environment": "production"}
)
```

### 3. DataItem

Represents an item in a data source (file, table, etc.):

```python
@dataclass
class DataItem:
    name: str                    # Name of the item
    path: str                    # Full path or identifier
    size: int                    # Size in bytes
    modified_at: int             # Unix timestamp
    metadata: Dict[str, Any]     # Additional metadata
```

**Example:**

```python
item = DataItem(
    name="sales_data.csv",
    path="/data/2024/sales_data.csv",
    size=1048576,  # 1 MB
    modified_at=1234567890,
    metadata={"content_type": "text/csv", "encoding": "utf-8"}
)
```

### 4. DataSourceConnector

Abstract base class that all connectors must implement:

```python
class DataSourceConnector(ABC):
    async def connect(self) -> bool
    async def disconnect(self) -> None
    async def test_connection(self) -> bool
    async def list_items(self, path: Optional[str] = None) -> List[DataItem]
    async def fetch_data(self, identifier: str, workspace: str) -> str
    async def get_metadata(self, identifier: str) -> Dict[str, Any]
```

## Exception Hierarchy

```
DataSourceError (Base Exception)
    ├── ConnectionError (Connection failures)
    ├── AuthenticationError (Authentication failures)
    └── DataFetchError (Data fetching failures)
```

## Implementing a New Connector

To implement a new data source connector:

1. **Create a new file** in `API/datasources/` (e.g., `my_connector.py`)

2. **Import the base class:**

```python
from .base import DataSourceConnector, DataSourceConfig, DataItem
```

3. **Implement all abstract methods:**

```python
class MyConnector(DataSourceConnector):
    async def connect(self) -> bool:
        # Establish connection
        # Set self._connection
        return True
    
    async def disconnect(self) -> None:
        # Close connection
        # Set self._connection = None
        pass
    
    async def test_connection(self) -> bool:
        # Verify connection is valid
        return self._connection is not None
    
    async def list_items(self, path: Optional[str] = None) -> List[DataItem]:
        # List available items
        return []
    
    async def fetch_data(self, identifier: str, workspace: str) -> str:
        # Fetch data and save to workspace
        return "/path/to/saved/file"
    
    async def get_metadata(self, identifier: str) -> Dict[str, Any]:
        # Get metadata for item
        return {}
```

4. **Register the connector** in the registry (to be implemented)

## Usage Examples

### Basic Usage

```python
from datasources import DataSourceConfig, DataSourceType
from datasources.azure_blob import AzureBlobConnector

# Create configuration
config = DataSourceConfig(
    id="ds-123",
    type=DataSourceType.AZURE_BLOB,
    name="My Azure Storage",
    config={"connection_string": "..."}
)

# Create connector
connector = AzureBlobConnector(config)

# Connect
await connector.connect()

# List items
items = await connector.list_items()
for item in items:
    print(f"{item.name}: {item.size} bytes")

# Fetch data
local_path = await connector.fetch_data("data.csv", "/workspace")
print(f"Data saved to: {local_path}")

# Disconnect
await connector.disconnect()
```

### Using Context Manager

```python
async with AzureBlobConnector(config) as connector:
    items = await connector.list_items()
    for item in items:
        path = await connector.fetch_data(item.path, "/workspace")
        print(f"Downloaded: {path}")
# Connection automatically closed
```

### Error Handling

```python
from datasources import ConnectionError, AuthenticationError, DataFetchError

try:
    async with connector:
        await connector.fetch_data("file.csv", "/workspace")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except ConnectionError as e:
    print(f"Connection failed: {e}")
except DataFetchError as e:
    print(f"Failed to fetch data: {e}")
```

## Testing

Run the test suite:

```bash
python API/datasources/test_base.py
```

## Design Principles

1. **Extensibility**: Easy to add new data source types
2. **Async/Await**: Non-blocking I/O for better performance
3. **Type Safety**: Strong typing with dataclasses and type hints
4. **Error Handling**: Clear exception hierarchy
5. **Context Managers**: Automatic resource cleanup
6. **Testability**: Abstract interface allows easy mocking

## Next Steps

- [ ] Implement Azure Blob Storage connector
- [ ] Implement PostgreSQL connector
- [ ] Implement credential manager
- [ ] Implement data source registry
- [ ] Add connection pooling
- [ ] Create API endpoints for data source management

## References

- Design Document: `.kiro/specs/data-sources-extension/design.md`
- Requirements: `.kiro/specs/data-sources-extension/requirements.md`
