"""
Unit tests for Connection Pool Manager
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .pool import (
    ConnectionPool,
    ConnectionPoolManager,
    PoolConfig,
    PooledConnection,
    PoolError,
)
from .base import (
    DataSourceConnector,
    DataSourceConfig,
    DataSourceType,
    DataItem,
    ConnectionError as DSConnectionError,
)


# Mock connector for testing
class MockConnector(DataSourceConnector):
    """Mock connector for testing purposes"""
    
    _instance_count = 0
    
    def __init__(self, config: DataSourceConfig, should_fail: bool = False):
        super().__init__(config)
        self.should_fail = should_fail
        self.connect_called = False
        self.disconnect_called = False
        self.test_connection_called = False
        MockConnector._instance_count += 1
        self.instance_id = MockConnector._instance_count
    
    async def connect(self) -> bool:
        self.connect_called = True
        if self.should_fail:
            raise DSConnectionError("Mock connection failed")
        self._connection = f"mock_connection_{self.instance_id}"
        await asyncio.sleep(0.01)  # Simulate connection delay
        return True
    
    async def disconnect(self) -> None:
        self.disconnect_called = True
        self._connection = None
        await asyncio.sleep(0.01)  # Simulate disconnection delay
    
    async def test_connection(self) -> bool:
        self.test_connection_called = True
        if self.should_fail:
            return False
        return self._connection is not None
    
    async def list_items(self, path: Optional[str] = None) -> List[DataItem]:
        return []
    
    async def fetch_data(self, identifier: str, workspace: str) -> str:
        return "/mock/path"
    
    async def get_metadata(self, identifier: str) -> Dict[str, Any]:
        return {}


@pytest.fixture
def sample_config():
    """Create a sample data source configuration"""
    return DataSourceConfig(
        id="test-ds-1",
        type=DataSourceType.AZURE_BLOB,
        name="Test Data Source",
        config={
            "connection_string": "test_connection",
            "container": "test-container"
        }
    )


@pytest.fixture
def connector_factory(sample_config):
    """Create a connector factory function"""
    def factory():
        return MockConnector(sample_config)
    return factory


@pytest.fixture
def pool_config():
    """Create a pool configuration for testing"""
    return PoolConfig(
        max_size=5,
        min_size=1,
        max_idle_time=10,
        acquire_timeout=5,
        max_lifetime=30
    )


class TestPoolConfig:
    """Test suite for PoolConfig"""
    
    def test_default_values(self):
        """Test default pool configuration values"""
        config = PoolConfig()
        
        assert config.max_size == 10
        assert config.min_size == 1
        assert config.max_idle_time == 300
        assert config.acquire_timeout == 30
        assert config.max_lifetime == 3600
    
    def test_custom_values(self):
        """Test custom pool configuration values"""
        config = PoolConfig(
            max_size=20,
            min_size=5,
            max_idle_time=600,
            acquire_timeout=60,
            max_lifetime=7200
        )
        
        assert config.max_size == 20
        assert config.min_size == 5
        assert config.max_idle_time == 600
        assert config.acquire_timeout == 60
        assert config.max_lifetime == 7200


class TestPooledConnection:
    """Test suite for PooledConnection"""
    
    def test_initialization(self, sample_config):
        """Test pooled connection initialization"""
        connector = MockConnector(sample_config)
        pooled = PooledConnection(connector=connector)
        
        assert pooled.connector is connector
        assert pooled.in_use is False
        assert pooled.use_count == 0
        assert isinstance(pooled.created_at, datetime)
        assert isinstance(pooled.last_used, datetime)
    
    def test_is_expired(self, sample_config):
        """Test connection expiration check"""
        connector = MockConnector(sample_config)
        pooled = PooledConnection(connector=connector)
        
        # Not expired immediately
        assert not pooled.is_expired(max_lifetime=10)
        
        # Simulate old connection
        pooled.created_at = datetime.now() - timedelta(seconds=20)
        assert pooled.is_expired(max_lifetime=10)
    
    def test_is_idle_too_long(self, sample_config):
        """Test idle time check"""
        connector = MockConnector(sample_config)
        pooled = PooledConnection(connector=connector)
        
        # Not idle too long immediately
        assert not pooled.is_idle_too_long(max_idle_time=10)
        
        # Simulate idle connection
        pooled.last_used = datetime.now() - timedelta(seconds=20)
        assert pooled.is_idle_too_long(max_idle_time=10)
    
    def test_is_idle_too_long_in_use(self, sample_config):
        """Test that in-use connections are never considered idle"""
        connector = MockConnector(sample_config)
        pooled = PooledConnection(connector=connector)
        
        pooled.in_use = True
        pooled.last_used = datetime.now() - timedelta(seconds=20)
        
        # Should not be idle even though last_used is old
        assert not pooled.is_idle_too_long(max_idle_time=10)
    
    def test_mark_used(self, sample_config):
        """Test marking connection as used"""
        connector = MockConnector(sample_config)
        pooled = PooledConnection(connector=connector)
        
        initial_count = pooled.use_count
        pooled.mark_used()
        
        assert pooled.in_use is True
        assert pooled.use_count == initial_count + 1
    
    def test_mark_released(self, sample_config):
        """Test marking connection as released"""
        connector = MockConnector(sample_config)
        pooled = PooledConnection(connector=connector)
        
        pooled.in_use = True
        pooled.mark_released()
        
        assert pooled.in_use is False


class TestConnectionPool:
    """Test suite for ConnectionPool"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, connector_factory, pool_config):
        """Test pool initialization"""
        pool = ConnectionPool("test-ds-1", connector_factory, pool_config)
        await pool.initialize()
        
        try:
            assert pool.data_source_id == "test-ds-1"
            assert pool.size() >= pool_config.min_size
            assert pool.available_count() >= pool_config.min_size
        finally:
            await pool.close()
    
    @pytest.mark.asyncio
    async def test_acquire_connection(self, connector_factory, pool_config):
        """Test acquiring a connection from the pool"""
        pool = ConnectionPool("test-ds-1", connector_factory, pool_config)
        await pool.initialize()
        
        try:
            connector = await pool.acquire()
            
            assert connector is not None
            assert connector.is_connected()
            assert pool.in_use_count() == 1
            
            await pool.release(connector)
        finally:
            await pool.close()
    
    @pytest.mark.asyncio
    async def test_acquire_multiple_connections(self, connector_factory, pool_config):
        """Test acquiring multiple connections"""
        pool = ConnectionPool("test-ds-1", connector_factory, pool_config)
        await pool.initialize()
        
        try:
            connectors = []
            for _ in range(3):
                conn = await pool.acquire()
                connectors.append(conn)
            
            assert pool.in_use_count() == 3
            assert pool.size() >= 3
            
            # Release all
            for conn in connectors:
                await pool.release(conn)
            
            assert pool.in_use_count() == 0
        finally:
            await pool.close()
    
    @pytest.mark.asyncio
    async def test_acquire_respects_max_size(self, connector_factory):
        """Test that pool respects maximum size"""
        config = PoolConfig(max_size=2, min_size=1, acquire_timeout=1)
        pool = ConnectionPool("test-ds-1", connector_factory, config)
        await pool.initialize()
        
        try:
            # Acquire max connections
            conn1 = await pool.acquire()
            conn2 = await pool.acquire()
            
            assert pool.size() == 2
            
            # Try to acquire one more - should timeout
            with pytest.raises(PoolError, match="Timeout"):
                await pool.acquire(timeout=0.5)
            
            # Release one
            await pool.release(conn1)
            
            # Now should be able to acquire
            conn3 = await pool.acquire(timeout=0.5)
            assert conn3 is not None
            
            await pool.release(conn2)
            await pool.release(conn3)
        finally:
            await pool.close()
    
    @pytest.mark.asyncio
    async def test_release_connection(self, connector_factory, pool_config):
        """Test releasing a connection back to the pool"""
        pool = ConnectionPool("test-ds-1", connector_factory, pool_config)
        await pool.initialize()
        
        try:
            connector = await pool.acquire()
            initial_available = pool.available_count()
            
            await pool.release(connector)
            
            assert pool.in_use_count() == 0
            assert pool.available_count() > initial_available
        finally:
            await pool.close()
    
    @pytest.mark.asyncio
    async def test_release_unhealthy_connection(self, sample_config, pool_config):
        """Test releasing an unhealthy connection removes it from pool"""
        def factory():
            return MockConnector(sample_config, should_fail=False)
        
        pool = ConnectionPool("test-ds-1", factory, pool_config)
        await pool.initialize()
        
        try:
            connector = await pool.acquire()
            initial_size = pool.size()
            
            # Make connector unhealthy
            connector.should_fail = True
            
            await pool.release(connector)
            
            # Connection should be removed
            assert pool.size() < initial_size
        finally:
            await pool.close()
    
    @pytest.mark.asyncio
    async def test_connection_reuse(self, connector_factory, pool_config):
        """Test that connections are reused"""
        pool = ConnectionPool("test-ds-1", connector_factory, pool_config)
        await pool.initialize()
        
        try:
            # Acquire and release
            conn1 = await pool.acquire()
            conn1_id = id(conn1)
            await pool.release(conn1)
            
            # Acquire again - should get same connection
            conn2 = await pool.acquire()
            conn2_id = id(conn2)
            
            assert conn1_id == conn2_id
            
            await pool.release(conn2)
        finally:
            await pool.close()
    
    @pytest.mark.asyncio
    async def test_close_pool(self, connector_factory, pool_config):
        """Test closing the pool"""
        pool = ConnectionPool("test-ds-1", connector_factory, pool_config)
        await pool.initialize()
        
        # Acquire some connections
        conn1 = await pool.acquire()
        conn2 = await pool.acquire()
        
        await pool.close()
        
        assert pool._closed is True
        assert pool.size() == 0
        assert conn1.disconnect_called
        assert conn2.disconnect_called
    
    @pytest.mark.asyncio
    async def test_acquire_from_closed_pool(self, connector_factory, pool_config):
        """Test that acquiring from closed pool raises error"""
        pool = ConnectionPool("test-ds-1", connector_factory, pool_config)
        await pool.initialize()
        await pool.close()
        
        with pytest.raises(PoolError, match="closed"):
            await pool.acquire()
    
    @pytest.mark.asyncio
    async def test_pool_stats(self, connector_factory, pool_config):
        """Test pool statistics"""
        pool = ConnectionPool("test-ds-1", connector_factory, pool_config)
        await pool.initialize()
        
        try:
            initial_size = pool.size()
            
            conn1 = await pool.acquire()
            conn2 = await pool.acquire()
            
            assert pool.size() >= 2
            assert pool.in_use_count() == 2
            assert pool.available_count() == pool.size() - 2
            
            await pool.release(conn1)
            
            assert pool.in_use_count() == 1
            assert pool.available_count() == pool.size() - 1
            
            await pool.release(conn2)
        finally:
            await pool.close()
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_connections(self, connector_factory):
        """Test cleanup of expired connections"""
        config = PoolConfig(max_size=5, min_size=1, max_lifetime=1)
        pool = ConnectionPool("test-ds-1", connector_factory, config)
        await pool.initialize()
        
        try:
            # Acquire and release to create connections
            conn = await pool.acquire()
            await pool.release(conn)
            
            initial_size = pool.size()
            
            # Wait for connections to expire
            await asyncio.sleep(2)
            
            # Trigger cleanup
            await pool._cleanup_connections()
            
            # Should have removed expired connections but kept minimum
            assert pool.size() >= config.min_size
        finally:
            await pool.close()
    
    @pytest.mark.asyncio
    async def test_cleanup_idle_connections(self, connector_factory):
        """Test cleanup of idle connections"""
        config = PoolConfig(max_size=5, min_size=1, max_idle_time=1)
        pool = ConnectionPool("test-ds-1", connector_factory, config)
        await pool.initialize()
        
        try:
            # Create extra connections
            conns = []
            for _ in range(3):
                conn = await pool.acquire()
                conns.append(conn)
            
            for conn in conns:
                await pool.release(conn)
            
            initial_size = pool.size()
            assert initial_size >= 3
            
            # Wait for connections to become idle
            await asyncio.sleep(2)
            
            # Trigger cleanup
            await pool._cleanup_connections()
            
            # Should have removed idle connections but kept minimum
            assert pool.size() >= config.min_size
            assert pool.size() < initial_size
        finally:
            await pool.close()


class TestConnectionPoolManager:
    """Test suite for ConnectionPoolManager"""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test pool manager initialization"""
        manager = ConnectionPoolManager()
        
        assert manager is not None
        assert len(manager._pools) == 0
    
    @pytest.mark.asyncio
    async def test_get_pool_creates_new(self, connector_factory, pool_config):
        """Test getting pool creates new pool"""
        manager = ConnectionPoolManager()
        
        try:
            pool = await manager.get_pool("test-ds-1", connector_factory, pool_config)
            
            assert pool is not None
            assert pool.data_source_id == "test-ds-1"
            assert "test-ds-1" in manager._pools
        finally:
            await manager.close_all()
    
    @pytest.mark.asyncio
    async def test_get_pool_reuses_existing(self, connector_factory, pool_config):
        """Test getting pool reuses existing pool"""
        manager = ConnectionPoolManager()
        
        try:
            pool1 = await manager.get_pool("test-ds-1", connector_factory, pool_config)
            pool2 = await manager.get_pool("test-ds-1", connector_factory, pool_config)
            
            assert pool1 is pool2
        finally:
            await manager.close_all()
    
    @pytest.mark.asyncio
    async def test_close_pool(self, connector_factory, pool_config):
        """Test closing a specific pool"""
        manager = ConnectionPoolManager()
        
        await manager.get_pool("test-ds-1", connector_factory, pool_config)
        await manager.get_pool("test-ds-2", connector_factory, pool_config)
        
        assert len(manager._pools) == 2
        
        await manager.close_pool("test-ds-1")
        
        assert len(manager._pools) == 1
        assert "test-ds-1" not in manager._pools
        assert "test-ds-2" in manager._pools
        
        await manager.close_all()
    
    @pytest.mark.asyncio
    async def test_close_all_pools(self, connector_factory, pool_config):
        """Test closing all pools"""
        manager = ConnectionPoolManager()
        
        await manager.get_pool("test-ds-1", connector_factory, pool_config)
        await manager.get_pool("test-ds-2", connector_factory, pool_config)
        await manager.get_pool("test-ds-3", connector_factory, pool_config)
        
        assert len(manager._pools) == 3
        
        await manager.close_all()
        
        assert len(manager._pools) == 0
    
    @pytest.mark.asyncio
    async def test_get_pool_stats(self, connector_factory, pool_config):
        """Test getting pool statistics"""
        manager = ConnectionPoolManager()
        
        try:
            pool = await manager.get_pool("test-ds-1", connector_factory, pool_config)
            
            stats = manager.get_pool_stats("test-ds-1")
            
            assert stats is not None
            assert "total" in stats
            assert "available" in stats
            assert "in_use" in stats
            assert "max_size" in stats
            assert "min_size" in stats
            assert stats["max_size"] == pool_config.max_size
            assert stats["min_size"] == pool_config.min_size
        finally:
            await manager.close_all()
    
    @pytest.mark.asyncio
    async def test_get_pool_stats_nonexistent(self):
        """Test getting stats for nonexistent pool"""
        manager = ConnectionPoolManager()
        
        stats = manager.get_pool_stats("nonexistent")
        
        assert stats is None
    
    @pytest.mark.asyncio
    async def test_list_pools(self, connector_factory, pool_config):
        """Test listing all pools"""
        manager = ConnectionPoolManager()
        
        try:
            await manager.get_pool("test-ds-1", connector_factory, pool_config)
            await manager.get_pool("test-ds-2", connector_factory, pool_config)
            
            pools = manager.list_pools()
            
            assert len(pools) == 2
            assert "test-ds-1" in pools
            assert "test-ds-2" in pools
        finally:
            await manager.close_all()
    
    @pytest.mark.asyncio
    async def test_concurrent_pool_access(self, connector_factory, pool_config):
        """Test concurrent access to pools"""
        manager = ConnectionPoolManager()
        
        try:
            # Create multiple pools concurrently
            tasks = [
                manager.get_pool(f"test-ds-{i}", connector_factory, pool_config)
                for i in range(5)
            ]
            
            pools = await asyncio.gather(*tasks)
            
            assert len(pools) == 5
            assert len(manager._pools) == 5
        finally:
            await manager.close_all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
