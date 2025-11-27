"""
Tests for base connector interface
Verifies that the base classes and data structures work correctly
"""

import asyncio
from typing import List, Dict, Any, Optional
from .base import (
    DataSourceType,
    DataSourceConfig,
    DataItem,
    DataSourceConnector,
    DataSourceError,
    ConnectionError,
    AuthenticationError,
    DataFetchError,
)


class MockConnector(DataSourceConnector):
    """Mock connector for testing the base interface"""
    
    async def connect(self) -> bool:
        """Mock connect implementation"""
        self._connection = "mock_connection"
        return True
    
    async def disconnect(self) -> None:
        """Mock disconnect implementation"""
        self._connection = None
    
    async def test_connection(self) -> bool:
        """Mock test connection implementation"""
        return self._connection is not None
    
    async def list_items(self, path: Optional[str] = None) -> List[DataItem]:
        """Mock list items implementation"""
        return [
            DataItem(
                name="test_file.csv",
                path="/data/test_file.csv",
                size=1024,
                modified_at=1234567890,
                metadata={"type": "csv"}
            )
        ]
    
    async def fetch_data(self, identifier: str, workspace: str) -> str:
        """Mock fetch data implementation"""
        return f"{workspace}/{identifier}"
    
    async def get_metadata(self, identifier: str) -> Dict[str, Any]:
        """Mock get metadata implementation"""
        return {
            "name": identifier,
            "size": 1024,
            "type": "file"
        }


def test_data_source_type():
    """Test DataSourceType enum"""
    assert DataSourceType.AZURE_BLOB.value == "azure_blob"
    assert DataSourceType.POSTGRESQL.value == "postgresql"
    assert DataSourceType.LOCAL_FILE.value == "local_file"
    print("✓ DataSourceType enum works correctly")


def test_data_source_config():
    """Test DataSourceConfig dataclass"""
    config = DataSourceConfig(
        id="ds-123",
        type=DataSourceType.AZURE_BLOB,
        name="Test Azure Blob",
        config={"connection_string": "test"},
        metadata={"region": "us-east-1"}
    )
    
    assert config.id == "ds-123"
    assert config.type == DataSourceType.AZURE_BLOB
    assert config.name == "Test Azure Blob"
    assert config.config["connection_string"] == "test"
    assert config.metadata["region"] == "us-east-1"
    
    # Test to_dict
    config_dict = config.to_dict()
    assert config_dict["id"] == "ds-123"
    assert config_dict["type"] == "azure_blob"
    
    # Test from_dict
    config2 = DataSourceConfig.from_dict(config_dict)
    assert config2.id == config.id
    assert config2.type == config.type
    
    print("✓ DataSourceConfig works correctly")


def test_data_item():
    """Test DataItem dataclass"""
    item = DataItem(
        name="test.csv",
        path="/data/test.csv",
        size=2048,
        modified_at=1234567890,
        metadata={"encoding": "utf-8"}
    )
    
    assert item.name == "test.csv"
    assert item.path == "/data/test.csv"
    assert item.size == 2048
    assert item.modified_at == 1234567890
    
    # Test to_dict
    item_dict = item.to_dict()
    assert item_dict["name"] == "test.csv"
    assert item_dict["size"] == 2048
    
    print("✓ DataItem works correctly")


def test_exceptions():
    """Test custom exceptions"""
    try:
        raise DataSourceError("Test error")
    except DataSourceError as e:
        assert str(e) == "Test error"
    
    try:
        raise ConnectionError("Connection failed")
    except ConnectionError as e:
        assert str(e) == "Connection failed"
    
    try:
        raise AuthenticationError("Auth failed")
    except AuthenticationError as e:
        assert str(e) == "Auth failed"
    
    try:
        raise DataFetchError("Fetch failed")
    except DataFetchError as e:
        assert str(e) == "Fetch failed"
    
    print("✓ Custom exceptions work correctly")


import pytest

@pytest.mark.asyncio
async def test_connector_interface():
    """Test DataSourceConnector interface with mock implementation"""
    config = DataSourceConfig(
        id="ds-test",
        type=DataSourceType.AZURE_BLOB,
        name="Test Connector",
        config={}
    )
    
    connector = MockConnector(config)
    
    # Test initial state
    assert not connector.is_connected()
    
    # Test connect
    result = await connector.connect()
    assert result is True
    assert connector.is_connected()
    
    # Test test_connection
    is_valid = await connector.test_connection()
    assert is_valid is True
    
    # Test list_items
    items = await connector.list_items()
    assert len(items) == 1
    assert items[0].name == "test_file.csv"
    
    # Test fetch_data
    path = await connector.fetch_data("test.csv", "/workspace")
    assert path == "/workspace/test.csv"
    
    # Test get_metadata
    metadata = await connector.get_metadata("test.csv")
    assert metadata["name"] == "test.csv"
    
    # Test disconnect
    await connector.disconnect()
    assert not connector.is_connected()
    
    print("✓ DataSourceConnector interface works correctly")


@pytest.mark.asyncio
async def test_context_manager():
    """Test async context manager support"""
    config = DataSourceConfig(
        id="ds-test",
        type=DataSourceType.AZURE_BLOB,
        name="Test Connector",
        config={}
    )
    
    async with MockConnector(config) as connector:
        assert connector.is_connected()
        items = await connector.list_items()
        assert len(items) == 1
    
    # Connection should be closed after context
    assert not connector.is_connected()
    
    print("✓ Async context manager works correctly")


def main():
    """Run all tests"""
    print("Testing base connector interface...\n")
    
    # Synchronous tests
    test_data_source_type()
    test_data_source_config()
    test_data_item()
    test_exceptions()
    
    # Asynchronous tests
    asyncio.run(test_connector_interface())
    asyncio.run(test_context_manager())
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    main()
