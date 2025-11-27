"""
Integration tests for Azure Blob Storage connector
Tests against real Azure Blob Storage or Azurite emulator

These tests require either:
1. Azurite emulator running locally (recommended for CI/CD)
2. Real Azure Storage account with credentials in environment variables

To run with Azurite:
    docker run -p 10000:10000 mcr.microsoft.com/azure-storage/azurite azurite-blob --blobHost 0.0.0.0
    
To run with real Azure:
    export AZURE_STORAGE_CONNECTION_STRING="your_connection_string"
    export AZURE_STORAGE_CONTAINER_NAME="test-container"

Run tests:
    pytest API/datasources/test_azure_blob_integration.py -v
    
Skip if no Azure available:
    pytest API/datasources/test_azure_blob_integration.py -v -m "not requires_azure"
"""

import os
import asyncio
import tempfile
import pytest
from datetime import datetime

from .azure_blob import AzureBlobConnector
from .base import (
    DataSourceConfig,
    DataSourceType,
    ConnectionError as DSConnectionError,
    AuthenticationError,
    DataFetchError,
)

# Azurite default connection string
AZURITE_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)

# Test container name
TEST_CONTAINER = "test-container"


def get_azure_config():
    """Get Azure configuration from environment or use Azurite defaults"""
    connection_string = os.getenv(
        "AZURE_STORAGE_CONNECTION_STRING",
        AZURITE_CONNECTION_STRING
    )
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", TEST_CONTAINER)
    
    return DataSourceConfig(
        id="azure-integration-test",
        type=DataSourceType.AZURE_BLOB,
        name="Integration Test Azure Blob",
        config={
            "connection_string": connection_string,
            "container_name": container_name
        }
    )


def is_azure_available():
    """Check if Azure Blob Storage or Azurite is available"""
    try:
        from azure.storage.blob import BlobServiceClient
        config = get_azure_config()
        client = BlobServiceClient.from_connection_string(
            config.config['connection_string']
        )
        # Try to get account info
        client.get_service_properties()
        return True
    except Exception:
        return False


# Mark all tests in this module as requiring Azure
pytestmark = pytest.mark.skipif(
    not is_azure_available(),
    reason="Azure Blob Storage or Azurite not available"
)


@pytest.fixture
async def azure_connector():
    """Create and connect to Azure Blob Storage"""
    config = get_azure_config()
    connector = AzureBlobConnector(config)
    
    # Ensure container exists
    from azure.storage.blob import BlobServiceClient
    client = BlobServiceClient.from_connection_string(
        config.config['connection_string']
    )
    container_client = client.get_container_client(config.config['container_name'])
    
    try:
        if not container_client.exists():
            container_client.create_container()
    except Exception as e:
        print(f"Warning: Could not create container: {e}")
    
    # Connect
    await connector.connect()
    
    yield connector
    
    # Cleanup
    await connector.disconnect()


@pytest.fixture
async def test_blob(azure_connector):
    """Create a test blob for testing"""
    from azure.storage.blob import BlobServiceClient
    
    config = azure_connector.config
    client = BlobServiceClient.from_connection_string(
        config.config['connection_string']
    )
    container_client = client.get_container_client(config.config['container_name'])
    
    # Create test blob
    blob_name = "test-data/sample.csv"
    blob_content = b"name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago"
    
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(blob_content, overwrite=True)
    
    yield blob_name
    
    # Cleanup
    try:
        blob_client.delete_blob()
    except Exception:
        pass


@pytest.mark.asyncio
async def test_integration_connect_real_azure(azure_connector):
    """Test connecting to real Azure Blob Storage"""
    assert azure_connector.is_connected()
    print("✓ Successfully connected to Azure Blob Storage")


@pytest.mark.asyncio
async def test_integration_test_connection(azure_connector):
    """Test the test_connection method with real Azure"""
    result = await azure_connector.test_connection()
    assert result is True
    print("✓ Connection test passed")


@pytest.mark.asyncio
async def test_integration_list_items_empty(azure_connector):
    """Test listing items in an empty container"""
    # List all items
    items = await azure_connector.list_items()
    
    # Should return a list (may be empty or have items from other tests)
    assert isinstance(items, list)
    print(f"✓ Listed {len(items)} items from container")


@pytest.mark.asyncio
async def test_integration_upload_and_list(azure_connector):
    """Test uploading a file and listing it"""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Integration test content\n")
        f.write("Line 2\n")
        temp_path = f.name
    
    try:
        # Upload the file
        blob_name = f"integration-test/upload-{datetime.now().timestamp()}.txt"
        uploaded_name = await azure_connector.upload_file(temp_path, blob_name=blob_name)
        
        assert uploaded_name == blob_name
        print(f"✓ Uploaded file as: {blob_name}")
        
        # List items with prefix
        items = await azure_connector.list_items(path="integration-test/")
        
        # Should find our uploaded file
        found = any(item.path == blob_name for item in items)
        assert found, f"Uploaded blob '{blob_name}' not found in listing"
        print(f"✓ Found uploaded blob in listing")
        
        # Cleanup
        from azure.storage.blob import BlobServiceClient
        client = BlobServiceClient.from_connection_string(
            azure_connector.config.config['connection_string']
        )
        container_client = client.get_container_client(
            azure_connector.config.config['container_name']
        )
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.delete_blob()
        
    finally:
        os.unlink(temp_path)


@pytest.mark.asyncio
async def test_integration_fetch_data(azure_connector, test_blob):
    """Test downloading a blob to workspace"""
    with tempfile.TemporaryDirectory() as workspace:
        # Download the blob
        local_path = await azure_connector.fetch_data(test_blob, workspace)
        
        # Verify file exists
        assert os.path.exists(local_path)
        assert local_path.endswith("sample.csv")
        print(f"✓ Downloaded blob to: {local_path}")
        
        # Verify content
        with open(local_path, 'r') as f:
            content = f.read()
            assert "name,age,city" in content
            assert "Alice" in content
            assert "Bob" in content
            print("✓ Downloaded content is correct")


@pytest.mark.asyncio
async def test_integration_get_metadata(azure_connector, test_blob):
    """Test getting metadata for a blob"""
    metadata = await azure_connector.get_metadata(test_blob)
    
    # Verify metadata structure
    assert "name" in metadata
    assert "size" in metadata
    assert "content_type" in metadata
    assert "last_modified" in metadata
    assert "etag" in metadata
    
    # Verify values
    assert metadata["name"] == test_blob
    assert metadata["size"] > 0
    print(f"✓ Retrieved metadata: {metadata['size']} bytes, {metadata['content_type']}")


@pytest.mark.asyncio
async def test_integration_upload_and_download_roundtrip(azure_connector):
    """Test uploading and downloading a file (round trip)"""
    # Create test content
    test_content = "Round trip test\nLine 1\nLine 2\nLine 3\n"
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(test_content)
        upload_path = f.name
    
    with tempfile.TemporaryDirectory() as workspace:
        try:
            # Upload
            blob_name = f"roundtrip-test/file-{datetime.now().timestamp()}.txt"
            uploaded_name = await azure_connector.upload_file(upload_path, blob_name=blob_name)
            print(f"✓ Uploaded: {uploaded_name}")
            
            # Download
            download_path = await azure_connector.fetch_data(blob_name, workspace)
            print(f"✓ Downloaded: {download_path}")
            
            # Verify content matches
            with open(download_path, 'r') as f:
                downloaded_content = f.read()
            
            assert downloaded_content == test_content
            print("✓ Round trip successful - content matches")
            
            # Cleanup
            from azure.storage.blob import BlobServiceClient
            client = BlobServiceClient.from_connection_string(
                azure_connector.config.config['connection_string']
            )
            container_client = client.get_container_client(
                azure_connector.config.config['container_name']
            )
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.delete_blob()
            
        finally:
            os.unlink(upload_path)


@pytest.mark.asyncio
async def test_integration_list_with_prefix(azure_connector, test_blob):
    """Test listing blobs with a path prefix"""
    # List with prefix that should match our test blob
    items = await azure_connector.list_items(path="test-data/")
    
    # Should find at least our test blob
    assert len(items) > 0
    found = any(item.path == test_blob for item in items)
    assert found, f"Test blob '{test_blob}' not found with prefix filter"
    print(f"✓ Found {len(items)} items with prefix 'test-data/'")


@pytest.mark.asyncio
async def test_integration_fetch_nonexistent_blob(azure_connector):
    """Test fetching a blob that doesn't exist"""
    with tempfile.TemporaryDirectory() as workspace:
        with pytest.raises(DataFetchError, match="does not exist"):
            await azure_connector.fetch_data("nonexistent/blob.txt", workspace)
    
    print("✓ Correctly raised error for nonexistent blob")


@pytest.mark.asyncio
async def test_integration_get_metadata_nonexistent(azure_connector):
    """Test getting metadata for nonexistent blob"""
    with pytest.raises(DataFetchError, match="not found"):
        await azure_connector.get_metadata("nonexistent/blob.txt")
    
    print("✓ Correctly raised error for nonexistent blob metadata")


@pytest.mark.asyncio
async def test_integration_upload_overwrite(azure_connector):
    """Test uploading with overwrite flag"""
    blob_name = f"overwrite-test/file-{datetime.now().timestamp()}.txt"
    
    # Create first file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("First version")
        first_path = f.name
    
    # Create second file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Second version")
        second_path = f.name
    
    try:
        # Upload first version
        await azure_connector.upload_file(first_path, blob_name=blob_name, overwrite=True)
        print("✓ Uploaded first version")
        
        # Upload second version (overwrite)
        await azure_connector.upload_file(second_path, blob_name=blob_name, overwrite=True)
        print("✓ Uploaded second version (overwrite)")
        
        # Download and verify it's the second version
        with tempfile.TemporaryDirectory() as workspace:
            download_path = await azure_connector.fetch_data(blob_name, workspace)
            with open(download_path, 'r') as f:
                content = f.read()
            
            assert content == "Second version"
            print("✓ Overwrite successful - got second version")
        
        # Cleanup
        from azure.storage.blob import BlobServiceClient
        client = BlobServiceClient.from_connection_string(
            azure_connector.config.config['connection_string']
        )
        container_client = client.get_container_client(
            azure_connector.config.config['container_name']
        )
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.delete_blob()
        
    finally:
        os.unlink(first_path)
        os.unlink(second_path)


@pytest.mark.asyncio
async def test_integration_context_manager(azure_connector):
    """Test using connector as async context manager"""
    config = get_azure_config()
    
    async with AzureBlobConnector(config) as connector:
        assert connector.is_connected()
        
        # Do some operation
        items = await connector.list_items()
        assert isinstance(items, list)
        print(f"✓ Context manager works - listed {len(items)} items")
    
    # Should be disconnected after context
    assert not connector.is_connected()
    print("✓ Connector properly disconnected after context")


@pytest.mark.asyncio
async def test_integration_multiple_operations(azure_connector, test_blob):
    """Test performing multiple operations in sequence"""
    # 1. List items
    items = await azure_connector.list_items()
    initial_count = len(items)
    print(f"✓ Initial count: {initial_count} items")
    
    # 2. Get metadata
    metadata = await azure_connector.get_metadata(test_blob)
    assert metadata["size"] > 0
    print(f"✓ Got metadata: {metadata['size']} bytes")
    
    # 3. Download blob
    with tempfile.TemporaryDirectory() as workspace:
        local_path = await azure_connector.fetch_data(test_blob, workspace)
        assert os.path.exists(local_path)
        print(f"✓ Downloaded to: {local_path}")
    
    # 4. Upload new blob
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Multi-op test")
        temp_path = f.name
    
    try:
        blob_name = f"multi-op-test/file-{datetime.now().timestamp()}.txt"
        await azure_connector.upload_file(temp_path, blob_name=blob_name)
        print(f"✓ Uploaded: {blob_name}")
        
        # 5. List again and verify count increased
        items = await azure_connector.list_items()
        assert len(items) >= initial_count + 1
        print(f"✓ Final count: {len(items)} items")
        
        # Cleanup
        from azure.storage.blob import BlobServiceClient
        client = BlobServiceClient.from_connection_string(
            azure_connector.config.config['connection_string']
        )
        container_client = client.get_container_client(
            azure_connector.config.config['container_name']
        )
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.delete_blob()
        
    finally:
        os.unlink(temp_path)


def main():
    """Run integration tests"""
    if not is_azure_available():
        print("⚠ Azure Blob Storage or Azurite not available")
        print("\nTo run integration tests:")
        print("1. Start Azurite emulator:")
        print("   docker run -p 10000:10000 mcr.microsoft.com/azure-storage/azurite azurite-blob --blobHost 0.0.0.0")
        print("\n2. Or set environment variables for real Azure:")
        print("   export AZURE_STORAGE_CONNECTION_STRING='your_connection_string'")
        print("   export AZURE_STORAGE_CONTAINER_NAME='test-container'")
        return
    
    print("Running Azure Blob Storage integration tests...\n")
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    main()
