"""
Tests for Azure Blob Storage connector
Tests the AzureBlobConnector implementation
"""

import os
import asyncio
import tempfile
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from .azure_blob import AzureBlobConnector
from .base import (
    DataSourceConfig,
    DataSourceType,
    ConnectionError as DSConnectionError,
    AuthenticationError,
    DataFetchError,
)


@pytest.fixture
def azure_config():
    """Create a test configuration for Azure Blob Storage"""
    return DataSourceConfig(
        id="azure-test-1",
        type=DataSourceType.AZURE_BLOB,
        name="Test Azure Blob",
        config={
            "connection_string": "DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=testkey;EndpointSuffix=core.windows.net",
            "container_name": "test-container"
        }
    )


@pytest.fixture
def azure_config_sas():
    """Create a test configuration using SAS token"""
    return DataSourceConfig(
        id="azure-test-2",
        type=DataSourceType.AZURE_BLOB,
        name="Test Azure Blob SAS",
        config={
            "account_url": "https://testaccount.blob.core.windows.net",
            "sas_token": "sv=2020-08-04&ss=b&srt=sco&sp=rwdlac&se=2024-12-31T23:59:59Z&st=2024-01-01T00:00:00Z&spr=https&sig=test",
            "container_name": "test-container"
        }
    )


@pytest.mark.asyncio
async def test_connect_with_connection_string(azure_config):
    """Test connecting to Azure Blob Storage with connection string"""
    connector = AzureBlobConnector(azure_config)
    
    with patch('API.datasources.azure_blob.BlobServiceClient') as mock_client_class:
        # Mock the BlobServiceClient
        mock_service_client = Mock()
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        # Mock container client - exists() is synchronous in Azure SDK
        mock_container_client = Mock()
        mock_container_client.exists = Mock(return_value=True)
        mock_service_client.get_container_client.return_value = mock_container_client
        
        # Connect
        result = await connector.connect()
        
        assert result is True
        assert connector.is_connected()
        mock_client_class.from_connection_string.assert_called_once()
        
    print("✓ Connect with connection string works")


@pytest.mark.asyncio
async def test_connect_with_sas_token(azure_config_sas):
    """Test connecting to Azure Blob Storage with SAS token"""
    connector = AzureBlobConnector(azure_config_sas)
    
    with patch('API.datasources.azure_blob.BlobServiceClient') as mock_client_class:
        # Mock the BlobServiceClient
        mock_service_client = Mock()
        mock_client_class.return_value = mock_service_client
        
        # Mock container client
        mock_container_client = Mock()
        mock_container_client.exists = Mock(return_value=True)
        mock_service_client.get_container_client.return_value = mock_container_client
        
        # Connect
        result = await connector.connect()
        
        assert result is True
        assert connector.is_connected()
        mock_client_class.assert_called_once()
        
    print("✓ Connect with SAS token works")


@pytest.mark.asyncio
async def test_connect_missing_container_name():
    """Test that connection fails when container_name is missing"""
    config = DataSourceConfig(
        id="azure-test-3",
        type=DataSourceType.AZURE_BLOB,
        name="Test Azure Blob",
        config={
            "connection_string": "test_connection_string"
            # Missing container_name
        }
    )
    
    connector = AzureBlobConnector(config)
    
    with pytest.raises(DSConnectionError, match="container_name is required"):
        await connector.connect()
    
    print("✓ Missing container_name raises error")


@pytest.mark.asyncio
async def test_connect_missing_credentials():
    """Test that connection fails when credentials are missing"""
    config = DataSourceConfig(
        id="azure-test-4",
        type=DataSourceType.AZURE_BLOB,
        name="Test Azure Blob",
        config={
            "container_name": "test-container"
            # Missing connection_string and account_url
        }
    )
    
    connector = AzureBlobConnector(config)
    
    with pytest.raises(DSConnectionError, match="connection_string or account_url"):
        await connector.connect()
    
    print("✓ Missing credentials raises error")


@pytest.mark.asyncio
async def test_connect_container_not_found(azure_config):
    """Test that connection fails when container doesn't exist"""
    connector = AzureBlobConnector(azure_config)
    
    with patch('API.datasources.azure_blob.BlobServiceClient') as mock_client_class:
        mock_service_client = Mock()
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        # Mock container that doesn't exist
        mock_container_client = Mock()
        mock_container_client.exists = Mock(return_value=False)
        mock_service_client.get_container_client.return_value = mock_container_client
        
        with pytest.raises(DSConnectionError, match="does not exist"):
            await connector.connect()
    
    print("✓ Non-existent container raises error")


@pytest.mark.asyncio
async def test_disconnect(azure_config):
    """Test disconnecting from Azure Blob Storage"""
    connector = AzureBlobConnector(azure_config)
    
    with patch('API.datasources.azure_blob.BlobServiceClient') as mock_client_class:
        mock_service_client = Mock()
        mock_service_client.close = AsyncMock()
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        mock_container_client = Mock()
        mock_container_client.exists = Mock(return_value=True)
        mock_service_client.get_container_client.return_value = mock_container_client
        
        # Connect then disconnect
        await connector.connect()
        assert connector.is_connected()
        
        await connector.disconnect()
        assert not connector.is_connected()
        mock_service_client.close.assert_called_once()
    
    print("✓ Disconnect works correctly")


@pytest.mark.asyncio
async def test_test_connection(azure_config):
    """Test the test_connection method"""
    connector = AzureBlobConnector(azure_config)
    
    with patch('API.datasources.azure_blob.BlobServiceClient') as mock_client_class:
        mock_service_client = Mock()
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        mock_container_client = Mock()
        mock_container_client.exists = Mock(return_value=True)
        mock_service_client.get_container_client.return_value = mock_container_client
        
        # Test connection
        result = await connector.test_connection()
        
        assert result is True
    
    print("✓ Test connection works")


@pytest.mark.asyncio
async def test_list_items(azure_config):
    """Test listing blobs in container"""
    connector = AzureBlobConnector(azure_config)
    
    with patch('API.datasources.azure_blob.BlobServiceClient') as mock_client_class:
        mock_service_client = Mock()
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        # Create mock blobs
        mock_blob1 = Mock()
        mock_blob1.name = "data/file1.csv"
        mock_blob1.size = 1024
        mock_blob1.last_modified = datetime(2024, 1, 1, 12, 0, 0)
        mock_blob1.etag = "etag1"
        mock_blob1.blob_type = "BlockBlob"
        mock_blob1.content_settings = Mock(content_type="text/csv")
        
        mock_blob2 = Mock()
        mock_blob2.name = "data/file2.json"
        mock_blob2.size = 2048
        mock_blob2.last_modified = datetime(2024, 1, 2, 12, 0, 0)
        mock_blob2.etag = "etag2"
        mock_blob2.blob_type = "BlockBlob"
        mock_blob2.content_settings = Mock(content_type="application/json")
        
        # Mock async iterator for list_blobs
        async def mock_list_blobs(*args, **kwargs):
            for blob in [mock_blob1, mock_blob2]:
                yield blob
        
        mock_container_client = Mock()
        mock_container_client.exists = Mock(return_value=True)
        mock_container_client.list_blobs = mock_list_blobs
        mock_service_client.get_container_client.return_value = mock_container_client
        
        # Connect and list items
        await connector.connect()
        items = await connector.list_items()
        
        assert len(items) == 2
        assert items[0].name == "file1.csv"
        assert items[0].path == "data/file1.csv"
        assert items[0].size == 1024
        assert items[1].name == "file2.json"
        assert items[1].size == 2048
    
    print("✓ List items works correctly")


@pytest.mark.asyncio
async def test_list_items_with_prefix(azure_config):
    """Test listing blobs with path prefix"""
    connector = AzureBlobConnector(azure_config)
    
    with patch('API.datasources.azure_blob.BlobServiceClient') as mock_client_class:
        mock_service_client = Mock()
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        mock_blob = Mock()
        mock_blob.name = "data/subfolder/file.csv"
        mock_blob.size = 512
        mock_blob.last_modified = datetime(2024, 1, 1, 12, 0, 0)
        mock_blob.etag = "etag"
        mock_blob.blob_type = "BlockBlob"
        mock_blob.content_settings = Mock(content_type="text/csv")
        
        async def mock_list_blobs(*args, **kwargs):
            # Verify prefix was passed
            if kwargs.get('name_starts_with') == 'data/subfolder/':
                yield mock_blob
        
        mock_container_client = Mock()
        mock_container_client.exists = Mock(return_value=True)
        mock_container_client.list_blobs = mock_list_blobs
        mock_service_client.get_container_client.return_value = mock_container_client
        
        await connector.connect()
        items = await connector.list_items(path='data/subfolder/')
        
        assert len(items) == 1
        assert items[0].name == "file.csv"
    
    print("✓ List items with prefix works")


@pytest.mark.asyncio
async def test_fetch_data(azure_config):
    """Test downloading a blob to workspace"""
    connector = AzureBlobConnector(azure_config)
    
    with patch('API.datasources.azure_blob.BlobServiceClient') as mock_client_class:
        mock_service_client = Mock()
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        # Mock blob client
        mock_blob_client = AsyncMock()
        mock_blob_client.exists = AsyncMock(return_value=True)
        
        # Mock download stream
        mock_download_stream = AsyncMock()
        mock_download_stream.readall = AsyncMock(return_value=b"test,data\n1,2\n3,4")
        mock_blob_client.download_blob = AsyncMock(return_value=mock_download_stream)
        
        mock_container_client = Mock()
        mock_container_client.exists = Mock(return_value=True)
        mock_container_client.get_blob_client.return_value = mock_blob_client
        mock_service_client.get_container_client.return_value = mock_container_client
        
        # Create temporary workspace
        with tempfile.TemporaryDirectory() as workspace:
            await connector.connect()
            local_path = await connector.fetch_data("data/test.csv", workspace)
            
            # Verify file was created
            assert os.path.exists(local_path)
            assert local_path.endswith("test.csv")
            
            # Verify content
            with open(local_path, 'r') as f:
                content = f.read()
                assert "test,data" in content
    
    print("✓ Fetch data works correctly")


@pytest.mark.asyncio
async def test_fetch_data_blob_not_found(azure_config):
    """Test fetching non-existent blob"""
    connector = AzureBlobConnector(azure_config)
    
    with patch('API.datasources.azure_blob.BlobServiceClient') as mock_client_class:
        mock_service_client = Mock()
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        mock_blob_client = AsyncMock()
        mock_blob_client.exists = AsyncMock(return_value=False)
        
        mock_container_client = Mock()
        mock_container_client.exists = Mock(return_value=True)
        mock_container_client.get_blob_client.return_value = mock_blob_client
        mock_service_client.get_container_client.return_value = mock_container_client
        
        with tempfile.TemporaryDirectory() as workspace:
            await connector.connect()
            
            with pytest.raises(DataFetchError, match="does not exist"):
                await connector.fetch_data("nonexistent.csv", workspace)
    
    print("✓ Fetch non-existent blob raises error")


@pytest.mark.asyncio
async def test_get_metadata(azure_config):
    """Test getting blob metadata"""
    connector = AzureBlobConnector(azure_config)
    
    with patch('API.datasources.azure_blob.BlobServiceClient') as mock_client_class:
        mock_service_client = Mock()
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        # Mock blob properties
        mock_properties = Mock()
        mock_properties.size = 1024
        mock_properties.content_settings = Mock(content_type="text/csv")
        mock_properties.last_modified = datetime(2024, 1, 1, 12, 0, 0)
        mock_properties.etag = "etag123"
        mock_properties.blob_type = "BlockBlob"
        mock_properties.creation_time = datetime(2024, 1, 1, 10, 0, 0)
        mock_properties.metadata = {"author": "test"}
        
        mock_blob_client = AsyncMock()
        mock_blob_client.get_blob_properties = AsyncMock(return_value=mock_properties)
        
        mock_container_client = Mock()
        mock_container_client.exists = Mock(return_value=True)
        mock_container_client.get_blob_client.return_value = mock_blob_client
        mock_service_client.get_container_client.return_value = mock_container_client
        
        await connector.connect()
        metadata = await connector.get_metadata("test.csv")
        
        assert metadata["name"] == "test.csv"
        assert metadata["size"] == 1024
        assert metadata["content_type"] == "text/csv"
        assert metadata["blob_type"] == "BlockBlob"
        assert metadata["metadata"]["author"] == "test"
    
    print("✓ Get metadata works correctly")


@pytest.mark.asyncio
async def test_upload_file(azure_config):
    """Test uploading a file to Azure Blob Storage"""
    connector = AzureBlobConnector(azure_config)
    
    with patch('API.datasources.azure_blob.BlobServiceClient') as mock_client_class:
        mock_service_client = Mock()
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        mock_blob_client = AsyncMock()
        mock_blob_client.upload_blob = AsyncMock()
        
        mock_container_client = Mock()
        mock_container_client.exists = Mock(return_value=True)
        mock_container_client.get_blob_client.return_value = mock_blob_client
        mock_service_client.get_container_client.return_value = mock_container_client
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write("test,data\n1,2\n")
            temp_path = f.name
        
        try:
            await connector.connect()
            blob_name = await connector.upload_file(temp_path)
            
            assert blob_name == os.path.basename(temp_path)
            mock_blob_client.upload_blob.assert_called_once()
        finally:
            os.unlink(temp_path)
    
    print("✓ Upload file works correctly")


@pytest.mark.asyncio
async def test_upload_file_custom_name(azure_config):
    """Test uploading a file with custom blob name"""
    connector = AzureBlobConnector(azure_config)
    
    with patch('API.datasources.azure_blob.BlobServiceClient') as mock_client_class:
        mock_service_client = Mock()
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        mock_blob_client = AsyncMock()
        mock_blob_client.upload_blob = AsyncMock()
        
        mock_container_client = Mock()
        mock_container_client.exists = Mock(return_value=True)
        mock_container_client.get_blob_client.return_value = mock_blob_client
        mock_service_client.get_container_client.return_value = mock_container_client
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test data")
            temp_path = f.name
        
        try:
            await connector.connect()
            blob_name = await connector.upload_file(temp_path, blob_name="custom/path/file.csv")
            
            assert blob_name == "custom/path/file.csv"
        finally:
            os.unlink(temp_path)
    
    print("✓ Upload file with custom name works")


@pytest.mark.asyncio
async def test_context_manager(azure_config):
    """Test using connector as async context manager"""
    with patch('API.datasources.azure_blob.BlobServiceClient') as mock_client_class:
        mock_service_client = Mock()
        mock_service_client.close = AsyncMock()
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        mock_container_client = Mock()
        mock_container_client.exists = Mock(return_value=True)
        mock_service_client.get_container_client.return_value = mock_container_client
        
        async with AzureBlobConnector(azure_config) as connector:
            assert connector.is_connected()
        
        # Should be disconnected after context
        assert not connector.is_connected()
    
    print("✓ Context manager works correctly")


def main():
    """Run all tests"""
    print("Testing Azure Blob Storage connector...\n")
    
    # Run pytest
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    main()
