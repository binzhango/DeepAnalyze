"""
Unit tests for Data Source Registry
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .registry import DataSourceRegistry, RegistryError
from .base import (
    DataSourceConnector,
    DataSourceConfig,
    DataSourceType,
    DataItem,
    ConnectionError as DSConnectionError,
)
from .credentials import CredentialManager


# Mock connector for testing
class MockConnector(DataSourceConnector):
    """Mock connector for testing purposes"""
    
    def __init__(self, config: DataSourceConfig, should_fail: bool = False):
        super().__init__(config)
        self.should_fail = should_fail
        self.connect_called = False
        self.disconnect_called = False
        self.test_connection_called = False
    
    async def connect(self) -> bool:
        self.connect_called = True
        if self.should_fail:
            raise DSConnectionError("Mock connection failed")
        self._connection = "mock_connection"
        return True
    
    async def disconnect(self) -> None:
        self.disconnect_called = True
        self._connection = None
    
    async def test_connection(self) -> bool:
        self.test_connection_called = True
        if self.should_fail:
            return False
        return True
    
    async def list_items(self, path: Optional[str] = None) -> List[DataItem]:
        return []
    
    async def fetch_data(self, identifier: str, workspace: str) -> str:
        return "/mock/path"
    
    async def get_metadata(self, identifier: str) -> Dict[str, Any]:
        return {}


@pytest.fixture
def credential_manager():
    """Create a credential manager for testing"""
    return CredentialManager()


@pytest.fixture
def registry(credential_manager):
    """Create a registry instance for testing"""
    reg = DataSourceRegistry(credential_manager=credential_manager)
    # Register mock connector
    reg.register_connector_class(DataSourceType.AZURE_BLOB, MockConnector)
    reg.register_connector_class(DataSourceType.POSTGRESQL, MockConnector)
    return reg


@pytest.fixture
def sample_config():
    """Create a sample data source configuration"""
    return DataSourceConfig(
        id="test-ds-1",
        type=DataSourceType.AZURE_BLOB,
        name="Test Data Source",
        config={
            "connection_string": "secret_connection_string",
            "container": "test-container"
        },
        metadata={"description": "Test data source"}
    )


class TestDataSourceRegistry:
    """Test suite for DataSourceRegistry"""
    
    def test_initialization(self):
        """Test registry initialization"""
        reg = DataSourceRegistry()
        assert reg is not None
        assert len(reg._connectors) == 0
        assert len(reg._configs) == 0
        assert len(reg._connector_classes) == 0
    
    def test_register_connector_class(self, registry):
        """Test registering a connector class"""
        # Already registered in fixture, verify it exists
        assert DataSourceType.AZURE_BLOB in registry._connector_classes
        assert registry._connector_classes[DataSourceType.AZURE_BLOB] == MockConnector
    
    def test_register_connector_class_overwrite(self, registry):
        """Test overwriting an existing connector class"""
        # Register again - should log warning but succeed
        registry.register_connector_class(DataSourceType.AZURE_BLOB, MockConnector)
        assert registry._connector_classes[DataSourceType.AZURE_BLOB] == MockConnector
    
    @pytest.mark.asyncio
    async def test_register_data_source_success(self, registry, sample_config):
        """Test successful data source registration"""
        data_source_id = await registry.register_data_source(sample_config)
        
        assert data_source_id == sample_config.id
        assert registry.exists(sample_config.id)
        
        # Verify config is stored and encrypted
        stored_config = registry._configs[sample_config.id]
        assert "_encrypted" in stored_config.config
    
    @pytest.mark.asyncio
    async def test_register_data_source_without_test(self, registry, sample_config):
        """Test registering data source without connection test"""
        data_source_id = await registry.register_data_source(
            sample_config,
            test_connection=False
        )
        
        assert data_source_id == sample_config.id
        assert registry.exists(sample_config.id)
    
    @pytest.mark.asyncio
    async def test_register_data_source_duplicate_id(self, registry, sample_config):
        """Test registering data source with duplicate ID"""
        await registry.register_data_source(sample_config, test_connection=False)
        
        # Try to register again with same ID
        with pytest.raises(RegistryError, match="already exists"):
            await registry.register_data_source(sample_config, test_connection=False)
    
    @pytest.mark.asyncio
    async def test_register_data_source_unsupported_type(self, registry):
        """Test registering data source with unsupported type"""
        config = DataSourceConfig(
            id="test-ds-2",
            type=DataSourceType.LOCAL_FILE,  # Not registered
            name="Test",
            config={}
        )
        
        with pytest.raises(RegistryError, match="No connector class registered"):
            await registry.register_data_source(config, test_connection=False)
    
    @pytest.mark.asyncio
    async def test_register_data_source_connection_test_fails(self, registry):
        """Test registration when connection test fails"""
        # Create a config that will cause connection to fail
        config = DataSourceConfig(
            id="test-ds-fail",
            type=DataSourceType.AZURE_BLOB,
            name="Failing Data Source",
            config={"should_fail": True}
        )
        
        # Temporarily replace connector class with one that fails
        class FailingConnector(MockConnector):
            def __init__(self, config):
                super().__init__(config, should_fail=True)
        
        registry.register_connector_class(DataSourceType.AZURE_BLOB, FailingConnector)
        
        with pytest.raises(DSConnectionError):
            await registry.register_data_source(config, test_connection=True)
        
        # Restore original connector
        registry.register_connector_class(DataSourceType.AZURE_BLOB, MockConnector)
    
    @pytest.mark.asyncio
    async def test_unregister_data_source(self, registry, sample_config):
        """Test unregistering a data source"""
        await registry.register_data_source(sample_config, test_connection=False)
        assert registry.exists(sample_config.id)
        
        await registry.unregister_data_source(sample_config.id)
        assert not registry.exists(sample_config.id)
    
    @pytest.mark.asyncio
    async def test_unregister_nonexistent_data_source(self, registry):
        """Test unregistering a data source that doesn't exist"""
        with pytest.raises(RegistryError, match="not found"):
            await registry.unregister_data_source("nonexistent-id")
    
    @pytest.mark.asyncio
    async def test_unregister_with_active_connector(self, registry, sample_config):
        """Test unregistering data source with active connector"""
        await registry.register_data_source(sample_config, test_connection=False)
        
        # Get connector to create it
        connector = await registry.get_connector(sample_config.id)
        assert connector.is_connected()
        
        # Unregister should disconnect
        await registry.unregister_data_source(sample_config.id)
        assert connector.disconnect_called
        assert not registry.exists(sample_config.id)
    
    @pytest.mark.asyncio
    async def test_get_connector_creates_new(self, registry, sample_config):
        """Test getting connector creates new instance"""
        await registry.register_data_source(sample_config, test_connection=False)
        
        connector = await registry.get_connector(sample_config.id)
        
        assert connector is not None
        assert connector.is_connected()
        assert connector.connect_called
        assert sample_config.id in registry._connectors
    
    @pytest.mark.asyncio
    async def test_get_connector_reuses_existing(self, registry, sample_config):
        """Test getting connector reuses existing instance"""
        await registry.register_data_source(sample_config, test_connection=False)
        
        connector1 = await registry.get_connector(sample_config.id)
        connector2 = await registry.get_connector(sample_config.id)
        
        assert connector1 is connector2
    
    @pytest.mark.asyncio
    async def test_get_connector_reconnects_if_disconnected(self, registry, sample_config):
        """Test getting connector reconnects if disconnected"""
        await registry.register_data_source(sample_config, test_connection=False)
        
        connector = await registry.get_connector(sample_config.id)
        await connector.disconnect()
        
        # Reset flag
        connector.connect_called = False
        
        # Get connector again should reconnect
        connector2 = await registry.get_connector(sample_config.id)
        assert connector2 is connector
        assert connector.connect_called
    
    @pytest.mark.asyncio
    async def test_get_connector_nonexistent(self, registry):
        """Test getting connector for nonexistent data source"""
        with pytest.raises(RegistryError, match="not found"):
            await registry.get_connector("nonexistent-id")
    
    def test_get_config_sanitized(self, registry, sample_config):
        """Test getting config with sanitization"""
        asyncio.run(registry.register_data_source(sample_config, test_connection=False))
        
        config = registry.get_config(sample_config.id, sanitize=True)
        
        assert config.id == sample_config.id
        assert config.name == sample_config.name
        # Credentials should be redacted
        assert "***REDACTED***" in str(config.config)
    
    def test_get_config_decrypted(self, registry, sample_config):
        """Test getting config with decryption"""
        asyncio.run(registry.register_data_source(sample_config, test_connection=False))
        
        config = registry.get_config(sample_config.id, decrypt=True)
        
        assert config.id == sample_config.id
        assert config.config["connection_string"] == "secret_connection_string"
        assert config.config["container"] == "test-container"
    
    def test_get_config_nonexistent(self, registry):
        """Test getting config for nonexistent data source"""
        with pytest.raises(RegistryError, match="not found"):
            registry.get_config("nonexistent-id")
    
    def test_list_data_sources_empty(self, registry):
        """Test listing data sources when empty"""
        configs = registry.list_data_sources()
        assert len(configs) == 0
    
    def test_list_data_sources(self, registry, sample_config):
        """Test listing data sources"""
        asyncio.run(registry.register_data_source(sample_config, test_connection=False))
        
        # Register another
        config2 = DataSourceConfig(
            id="test-ds-2",
            type=DataSourceType.POSTGRESQL,
            name="Test DB",
            config={"host": "localhost"}
        )
        asyncio.run(registry.register_data_source(config2, test_connection=False))
        
        configs = registry.list_data_sources()
        
        assert len(configs) == 2
        assert any(c.id == sample_config.id for c in configs)
        assert any(c.id == config2.id for c in configs)
    
    def test_exists(self, registry, sample_config):
        """Test checking if data source exists"""
        assert not registry.exists(sample_config.id)
        
        asyncio.run(registry.register_data_source(sample_config, test_connection=False))
        
        assert registry.exists(sample_config.id)
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, registry, sample_config):
        """Test connection testing"""
        await registry.register_data_source(sample_config, test_connection=False)
        
        result = await registry.test_connection(sample_config.id)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self, registry):
        """Test connection testing with failure"""
        # Create failing connector
        class FailingConnector(MockConnector):
            def __init__(self, config):
                super().__init__(config, should_fail=True)
        
        registry.register_connector_class(DataSourceType.AZURE_BLOB, FailingConnector)
        
        config = DataSourceConfig(
            id="test-fail",
            type=DataSourceType.AZURE_BLOB,
            name="Failing",
            config={}
        )
        
        await registry.register_data_source(config, test_connection=False)
        result = await registry.test_connection(config.id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_test_connection_nonexistent(self, registry):
        """Test connection testing for nonexistent data source"""
        with pytest.raises(RegistryError, match="not found"):
            await registry.test_connection("nonexistent-id")
    
    @pytest.mark.asyncio
    async def test_disconnect_all(self, registry, sample_config):
        """Test disconnecting all connectors"""
        await registry.register_data_source(sample_config, test_connection=False)
        
        # Create another config
        config2 = DataSourceConfig(
            id="test-ds-2",
            type=DataSourceType.POSTGRESQL,
            name="Test DB",
            config={}
        )
        await registry.register_data_source(config2, test_connection=False)
        
        # Get connectors to create them
        connector1 = await registry.get_connector(sample_config.id)
        connector2 = await registry.get_connector(config2.id)
        
        # Disconnect all
        await registry.disconnect_all()
        
        assert connector1.disconnect_called
        assert connector2.disconnect_called
        assert len(registry._connectors) == 0
    
    def test_cache_metadata(self, registry):
        """Test caching metadata"""
        metadata = {"tables": ["table1", "table2"]}
        
        registry.cache_metadata("test-ds-1", metadata)
        
        cached = registry.get_cached_metadata("test-ds-1")
        assert cached == metadata
    
    def test_get_cached_metadata_nonexistent(self, registry):
        """Test getting cached metadata that doesn't exist"""
        cached = registry.get_cached_metadata("nonexistent")
        assert cached is None
    
    def test_get_cached_metadata_expired(self, registry):
        """Test getting expired cached metadata"""
        # Create registry with very short TTL
        reg = DataSourceRegistry(cache_ttl=0)
        
        metadata = {"test": "data"}
        reg.cache_metadata("test-ds-1", metadata)
        
        # Wait for expiration
        import time
        time.sleep(0.1)
        
        cached = reg.get_cached_metadata("test-ds-1")
        assert cached is None
    
    def test_clear_cache_specific(self, registry):
        """Test clearing cache for specific data source"""
        registry.cache_metadata("test-ds-1", {"data": 1})
        registry.cache_metadata("test-ds-2", {"data": 2})
        
        registry.clear_cache("test-ds-1")
        
        assert registry.get_cached_metadata("test-ds-1") is None
        assert registry.get_cached_metadata("test-ds-2") is not None
    
    def test_clear_cache_all(self, registry):
        """Test clearing all cache"""
        registry.cache_metadata("test-ds-1", {"data": 1})
        registry.cache_metadata("test-ds-2", {"data": 2})
        
        registry.clear_cache()
        
        assert registry.get_cached_metadata("test-ds-1") is None
        assert registry.get_cached_metadata("test-ds-2") is None
    
    def test_encrypt_decrypt_config(self, registry, sample_config):
        """Test config encryption and decryption"""
        encrypted = registry._encrypt_config(sample_config)
        
        # Should have encrypted marker
        assert "_encrypted" in encrypted.config
        
        # Decrypt
        decrypted = registry._decrypt_config(encrypted)
        
        # Should match original
        assert decrypted.config == sample_config.config
    
    def test_create_connector(self, registry, sample_config):
        """Test creating connector from config"""
        encrypted = registry._encrypt_config(sample_config)
        
        connector = registry._create_connector(encrypted)
        
        assert isinstance(connector, MockConnector)
        assert connector.config.id == sample_config.id
    
    def test_create_connector_unsupported_type(self, registry):
        """Test creating connector for unsupported type"""
        config = DataSourceConfig(
            id="test",
            type=DataSourceType.LOCAL_FILE,
            name="Test",
            config={}
        )
        
        with pytest.raises(RegistryError, match="No connector class registered"):
            registry._create_connector(config)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
