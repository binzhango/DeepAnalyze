# Azure Blob Storage Connector

## Overview

The Azure Blob Storage connector provides seamless integration with Microsoft Azure Blob Storage, allowing DeepAnalyze to directly access and analyze files stored in the cloud.

## Features

- ✅ Connection string and SAS token authentication
- ✅ List blobs with optional path prefix filtering
- ✅ Download blobs to local workspace
- ✅ Upload files to Azure Blob Storage
- ✅ Retrieve blob metadata (size, content type, last modified, etc.)
- ✅ Connection pooling and lifecycle management
- ✅ Comprehensive error handling
- ✅ Async/await support

## Installation

```bash
pip install azure-storage-blob
```

## Configuration

### Option 1: Connection String

```python
config = DataSourceConfig(
    id="azure-blob-1",
    type=DataSourceType.AZURE_BLOB,
    name="My Azure Storage",
    config={
        "connection_string": "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net",
        "container_name": "my-container"
    }
)
```

### Option 2: SAS Token

```python
config = DataSourceConfig(
    id="azure-blob-2",
    type=DataSourceType.AZURE_BLOB,
    name="My Azure Storage (SAS)",
    config={
        "account_url": "https://myaccount.blob.core.windows.net",
        "sas_token": "sv=2020-08-04&ss=b&srt=sco&sp=rwdlac&se=2024-12-31T23:59:59Z",
        "container_name": "my-container"
    }
)
```

### Option 3: Public Container

```python
config = DataSourceConfig(
    id="azure-blob-3",
    type=DataSourceType.AZURE_BLOB,
    name="Public Azure Storage",
    config={
        "account_url": "https://myaccount.blob.core.windows.net",
        "container_name": "public-container"
    }
)
```

## Usage

### Basic Usage

```python
import asyncio
from API.datasources import (
    DataSourceRegistry,
    DataSourceConfig,
    DataSourceType,
    AzureBlobConnector,
)

async def main():
    # Initialize registry
    registry = DataSourceRegistry()
    registry.register_connector_class(DataSourceType.AZURE_BLOB, AzureBlobConnector)
    
    # Create and register data source
    config = DataSourceConfig(
        id="azure-1",
        type=DataSourceType.AZURE_BLOB,
        name="My Storage",
        config={
            "connection_string": "...",
            "container_name": "my-container"
        }
    )
    
    await registry.register_data_source(config)
    
    # Get connector
    connector = await registry.get_connector("azure-1")
    
    # List blobs
    items = await connector.list_items()
    for item in items:
        print(f"{item.name}: {item.size} bytes")
    
    # Download a blob
    local_path = await connector.fetch_data("data/file.csv", "/tmp/workspace")
    print(f"Downloaded to: {local_path}")
    
    # Upload a file
    blob_name = await connector.upload_file("/tmp/result.csv", "results/output.csv")
    print(f"Uploaded as: {blob_name}")
    
    # Clean up
    await registry.disconnect_all()

asyncio.run(main())
```

### Direct Connector Usage

```python
async def direct_usage():
    config = DataSourceConfig(
        id="azure-1",
        type=DataSourceType.AZURE_BLOB,
        name="My Storage",
        config={
            "connection_string": "...",
            "container_name": "my-container"
        }
    )
    
    # Use as context manager
    async with AzureBlobConnector(config) as connector:
        items = await connector.list_items()
        print(f"Found {len(items)} blobs")
```

## API Reference

### `AzureBlobConnector`

#### Methods

##### `connect() -> bool`
Establish connection to Azure Blob Storage.

**Returns:** `True` if connection successful

**Raises:**
- `ConnectionError`: If connection fails
- `AuthenticationError`: If authentication fails

##### `disconnect() -> None`
Close connection to Azure Blob Storage.

##### `test_connection() -> bool`
Test if the connection is valid.

**Returns:** `True` if connection is valid, `False` otherwise

##### `list_items(path: Optional[str] = None) -> List[DataItem]`
List blobs in the container.

**Parameters:**
- `path`: Optional prefix to filter blobs (e.g., 'folder/')

**Returns:** List of `DataItem` objects

**Raises:**
- `DataFetchError`: If listing fails

##### `fetch_data(identifier: str, workspace: str) -> str`
Download a blob to the workspace.

**Parameters:**
- `identifier`: Blob name/path to download
- `workspace`: Local workspace directory path

**Returns:** Local file path where the blob was saved

**Raises:**
- `DataFetchError`: If download fails

##### `get_metadata(identifier: str) -> Dict[str, Any]`
Get metadata for a specific blob.

**Parameters:**
- `identifier`: Blob name/path

**Returns:** Dictionary containing blob metadata:
- `name`: Blob name
- `size`: Size in bytes
- `content_type`: MIME type
- `last_modified`: Unix timestamp
- `etag`: ETag value
- `blob_type`: Type of blob (BlockBlob, PageBlob, etc.)
- `creation_time`: Unix timestamp of creation
- `metadata`: Custom metadata dictionary

**Raises:**
- `DataFetchError`: If metadata retrieval fails

##### `upload_file(local_path: str, blob_name: Optional[str] = None, overwrite: bool = True) -> str`
Upload a file to Azure Blob Storage.

**Parameters:**
- `local_path`: Path to local file to upload
- `blob_name`: Name for the blob (if None, uses filename from local_path)
- `overwrite`: Whether to overwrite existing blob

**Returns:** Blob name/path of uploaded file

**Raises:**
- `DataFetchError`: If upload fails

## Configuration Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `connection_string` | Conditional | Azure Storage connection string (required if not using SAS) |
| `account_url` | Conditional | Azure Storage account URL (required if using SAS or public access) |
| `sas_token` | Optional | Shared Access Signature token |
| `container_name` | Yes | Name of the container to access |

## Error Handling

The connector provides specific exceptions for different error scenarios:

- `ConnectionError`: Connection to Azure failed
- `AuthenticationError`: Authentication failed (invalid credentials)
- `DataFetchError`: Failed to fetch, upload, or list data

Example:

```python
try:
    connector = await registry.get_connector("azure-1")
    items = await connector.list_items()
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except ConnectionError as e:
    print(f"Connection failed: {e}")
except DataFetchError as e:
    print(f"Failed to list items: {e}")
```

## Security Best Practices

1. **Use Environment Variables**: Store credentials in environment variables, not in code
   ```python
   import os
   config = {
       "connection_string": os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
       "container_name": "my-container"
   }
   ```

2. **Use SAS Tokens**: Prefer SAS tokens with limited permissions and expiration
   ```python
   config = {
       "account_url": "https://myaccount.blob.core.windows.net",
       "sas_token": os.getenv("AZURE_SAS_TOKEN"),
       "container_name": "my-container"
   }
   ```

3. **Sanitize Configs**: Use registry's sanitize feature when logging or displaying configs
   ```python
   sanitized = registry.get_config("azure-1", sanitize=True)
   print(sanitized.config)  # Credentials are masked
   ```

4. **Read-Only Access**: When possible, use read-only SAS tokens or credentials

## Performance Considerations

1. **Connection Pooling**: The registry automatically manages connection pooling
2. **Streaming Downloads**: Large files are streamed to disk, not loaded into memory
3. **Metadata Caching**: The registry caches metadata for improved performance
4. **Parallel Operations**: Use asyncio to perform multiple operations concurrently

Example of parallel downloads:

```python
async def download_multiple(connector, blob_paths, workspace):
    tasks = [
        connector.fetch_data(path, workspace)
        for path in blob_paths
    ]
    results = await asyncio.gather(*tasks)
    return results
```

## Testing

Run the test suite:

```bash
pytest API/datasources/test_azure_blob.py -v
```

Run with coverage:

```bash
pytest API/datasources/test_azure_blob.py --cov=API.datasources.azure_blob --cov-report=html
```

## Examples

See `example_azure_blob.py` for a complete working example.

## Troubleshooting

### Connection Fails

**Problem:** `ConnectionError: Failed to connect to Azure Blob Storage`

**Solutions:**
- Verify connection string or SAS token is correct
- Check that the container name exists
- Ensure network connectivity to Azure
- Verify firewall rules allow access

### Authentication Fails

**Problem:** `AuthenticationError: Failed to authenticate with Azure Blob Storage`

**Solutions:**
- Verify credentials are valid and not expired
- Check that SAS token has required permissions
- Ensure account key is correct

### Blob Not Found

**Problem:** `DataFetchError: Blob 'file.csv' does not exist`

**Solutions:**
- Verify blob name/path is correct (case-sensitive)
- List blobs to see available files
- Check that blob hasn't been deleted

### Container Not Found

**Problem:** `ConnectionError: Container 'my-container' does not exist or is not accessible`

**Solutions:**
- Verify container name is correct
- Check that container exists in the storage account
- Ensure credentials have access to the container

## Related Documentation

- [Azure Blob Storage Documentation](https://docs.microsoft.com/en-us/azure/storage/blobs/)
- [Azure SDK for Python](https://github.com/Azure/azure-sdk-for-python)
- [DataSourceRegistry Documentation](./README.md)
- [Connection Pooling](./POOLING.md)

