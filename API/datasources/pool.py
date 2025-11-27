"""
Connection Pool Manager for Data Sources
Provides efficient connection pooling and resource management
"""

import asyncio
import logging
from typing import Dict, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .base import DataSourceConnector, DataSourceError

logger = logging.getLogger(__name__)


class PoolError(DataSourceError):
    """Exception raised for connection pool errors"""
    pass


@dataclass
class PoolConfig:
    """Configuration for connection pool
    
    Attributes:
        max_size: Maximum number of connections in the pool
        min_size: Minimum number of connections to maintain
        max_idle_time: Maximum time (seconds) a connection can be idle before cleanup
        acquire_timeout: Maximum time (seconds) to wait for a connection
        max_lifetime: Maximum lifetime (seconds) for a connection before recreation
    """
    max_size: int = 10
    min_size: int = 1
    max_idle_time: int = 300  # 5 minutes
    acquire_timeout: int = 30  # 30 seconds
    max_lifetime: int = 3600  # 1 hour


@dataclass
class PooledConnection:
    """Wrapper for a pooled connection
    
    Attributes:
        connector: The actual data source connector
        created_at: When this connection was created
        last_used: When this connection was last used
        in_use: Whether this connection is currently in use
        use_count: Number of times this connection has been used
    """
    connector: DataSourceConnector
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    in_use: bool = False
    use_count: int = 0
    
    def __hash__(self):
        """Make PooledConnection hashable based on connector identity"""
        return hash(id(self.connector))
    
    def __eq__(self, other):
        """Compare PooledConnections based on connector identity"""
        if not isinstance(other, PooledConnection):
            return False
        return self.connector is other.connector
    
    def is_expired(self, max_lifetime: int) -> bool:
        """Check if connection has exceeded its maximum lifetime
        
        Args:
            max_lifetime: Maximum lifetime in seconds
            
        Returns:
            True if connection is expired, False otherwise
        """
        age = (datetime.now() - self.created_at).total_seconds()
        return age > max_lifetime
    
    def is_idle_too_long(self, max_idle_time: int) -> bool:
        """Check if connection has been idle too long
        
        Args:
            max_idle_time: Maximum idle time in seconds
            
        Returns:
            True if connection has been idle too long, False otherwise
        """
        if self.in_use:
            return False
        
        idle_time = (datetime.now() - self.last_used).total_seconds()
        return idle_time > max_idle_time
    
    def mark_used(self) -> None:
        """Mark connection as used and update timestamp"""
        self.in_use = True
        self.last_used = datetime.now()
        self.use_count += 1
    
    def mark_released(self) -> None:
        """Mark connection as released"""
        self.in_use = False
        self.last_used = datetime.now()


class ConnectionPool:
    """Connection pool for a single data source
    
    Manages a pool of connections to a specific data source, providing:
    - Connection reuse
    - Concurrent connection limiting
    - Automatic connection cleanup
    - Connection health checking
    
    Attributes:
        data_source_id: ID of the data source this pool manages
        config: Pool configuration
        _connections: Set of pooled connections
        _available: Queue of available connections
        _lock: Lock for thread-safe operations
        _connector_factory: Factory function to create new connectors
        _closed: Whether the pool is closed
    """
    
    def __init__(
        self,
        data_source_id: str,
        connector_factory,
        config: Optional[PoolConfig] = None
    ):
        """Initialize connection pool
        
        Args:
            data_source_id: ID of the data source
            connector_factory: Callable that creates new connector instances
            config: Pool configuration, uses defaults if None
        """
        self.data_source_id = data_source_id
        self.config = config or PoolConfig()
        self._connector_factory = connector_factory
        self._connections: Set[PooledConnection] = set()
        self._available: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._closed = False
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info(
            f"Connection pool created for {data_source_id} "
            f"(max_size={self.config.max_size}, min_size={self.config.min_size})"
        )
    
    async def initialize(self) -> None:
        """Initialize the pool by creating minimum connections"""
        async with self._lock:
            for _ in range(self.config.min_size):
                try:
                    conn = await self._create_connection()
                    self._connections.add(conn)
                    await self._available.put(conn)
                except Exception as e:
                    logger.error(
                        f"Failed to create initial connection for {self.data_source_id}: {e}"
                    )
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info(f"Pool initialized for {self.data_source_id}")
    
    async def acquire(self, timeout: Optional[float] = None) -> DataSourceConnector:
        """Acquire a connection from the pool
        
        Args:
            timeout: Maximum time to wait for a connection (uses config default if None)
            
        Returns:
            Connected DataSourceConnector instance
            
        Raises:
            PoolError: If pool is closed or timeout occurs
        """
        if self._closed:
            raise PoolError(f"Connection pool for {self.data_source_id} is closed")
        
        if timeout is None:
            timeout = self.config.acquire_timeout
        
        try:
            # Try to get an available connection
            conn = await asyncio.wait_for(
                self._get_or_create_connection(),
                timeout=timeout
            )
            
            conn.mark_used()
            logger.debug(
                f"Connection acquired from pool {self.data_source_id} "
                f"(in_use={self._count_in_use()}/{len(self._connections)})"
            )
            
            return conn.connector
            
        except asyncio.TimeoutError:
            raise PoolError(
                f"Timeout waiting for connection to {self.data_source_id} "
                f"(timeout={timeout}s)"
            )
    
    async def release(self, connector: DataSourceConnector) -> None:
        """Release a connection back to the pool
        
        Args:
            connector: The connector to release
        """
        if self._closed:
            # If pool is closed, just disconnect
            await connector.disconnect()
            return
        
        async with self._lock:
            # Find the pooled connection
            pooled_conn = None
            for conn in self._connections:
                if conn.connector is connector:
                    pooled_conn = conn
                    break
            
            if pooled_conn is None:
                logger.warning(
                    f"Attempted to release unknown connection to pool {self.data_source_id}"
                )
                return
            
            # Check if connection is still healthy
            try:
                is_healthy = await connector.test_connection()
                if not is_healthy:
                    logger.warning(
                        f"Connection to {self.data_source_id} is unhealthy, removing from pool"
                    )
                    await self._remove_connection(pooled_conn)
                    return
            except Exception as e:
                logger.error(
                    f"Error testing connection health for {self.data_source_id}: {e}"
                )
                await self._remove_connection(pooled_conn)
                return
            
            # Check if connection is expired
            if pooled_conn.is_expired(self.config.max_lifetime):
                logger.info(
                    f"Connection to {self.data_source_id} exceeded max lifetime, removing"
                )
                await self._remove_connection(pooled_conn)
                return
            
            # Mark as released and return to pool
            pooled_conn.mark_released()
            await self._available.put(pooled_conn)
            
            logger.debug(
                f"Connection released to pool {self.data_source_id} "
                f"(available={self._available.qsize()}/{len(self._connections)})"
            )
    
    async def close(self) -> None:
        """Close the pool and disconnect all connections"""
        if self._closed:
            return
        
        self._closed = True
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        async with self._lock:
            # Disconnect all connections
            for conn in self._connections:
                try:
                    await conn.connector.disconnect()
                except Exception as e:
                    logger.error(
                        f"Error disconnecting connection in pool {self.data_source_id}: {e}"
                    )
            
            self._connections.clear()
            
            # Clear the queue
            while not self._available.empty():
                try:
                    self._available.get_nowait()
                except asyncio.QueueEmpty:
                    break
        
        logger.info(f"Connection pool closed for {self.data_source_id}")
    
    def size(self) -> int:
        """Get current pool size
        
        Returns:
            Number of connections in the pool
        """
        return len(self._connections)
    
    def available_count(self) -> int:
        """Get number of available connections
        
        Returns:
            Number of available connections
        """
        return self._available.qsize()
    
    def in_use_count(self) -> int:
        """Get number of connections currently in use
        
        Returns:
            Number of connections in use
        """
        return self._count_in_use()
    
    async def _get_or_create_connection(self) -> PooledConnection:
        """Get an available connection or create a new one
        
        Returns:
            PooledConnection instance
            
        Raises:
            PoolError: If unable to create connection
        """
        # Try to get from available queue
        try:
            conn = self._available.get_nowait()
            return conn
        except asyncio.QueueEmpty:
            pass
        
        # Need to create a new connection
        async with self._lock:
            # Check if we can create more connections
            if len(self._connections) >= self.config.max_size:
                # Wait for a connection to become available
                conn = await self._available.get()
                return conn
            
            # Create new connection
            try:
                conn = await self._create_connection()
                self._connections.add(conn)
                logger.info(
                    f"Created new connection for {self.data_source_id} "
                    f"(pool_size={len(self._connections)})"
                )
                return conn
            except Exception as e:
                logger.error(
                    f"Failed to create connection for {self.data_source_id}: {e}"
                )
                raise PoolError(f"Failed to create connection: {e}") from e
    
    async def _create_connection(self) -> PooledConnection:
        """Create a new pooled connection
        
        Returns:
            PooledConnection instance
            
        Raises:
            Exception: If connection creation or connection fails
        """
        connector = self._connector_factory()
        await connector.connect()
        
        return PooledConnection(connector=connector)
    
    async def _remove_connection(self, conn: PooledConnection) -> None:
        """Remove a connection from the pool
        
        Args:
            conn: Connection to remove
        """
        try:
            await conn.connector.disconnect()
        except Exception as e:
            logger.error(
                f"Error disconnecting connection for {self.data_source_id}: {e}"
            )
        
        self._connections.discard(conn)
        
        logger.debug(
            f"Connection removed from pool {self.data_source_id} "
            f"(pool_size={len(self._connections)})"
        )
    
    def _count_in_use(self) -> int:
        """Count connections currently in use
        
        Returns:
            Number of connections in use
        """
        return sum(1 for conn in self._connections if conn.in_use)
    
    async def _cleanup_loop(self) -> None:
        """Background task to cleanup idle and expired connections"""
        while not self._closed:
            try:
                await asyncio.sleep(60)  # Run cleanup every minute
                await self._cleanup_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop for {self.data_source_id}: {e}")
    
    async def _cleanup_connections(self) -> None:
        """Clean up idle and expired connections"""
        async with self._lock:
            to_remove = []
            
            for conn in self._connections:
                # Skip connections in use
                if conn.in_use:
                    continue
                
                # Always keep minimum connections, even if expired
                remaining_after_removal = len(self._connections) - len(to_remove)
                if remaining_after_removal <= self.config.min_size:
                    continue
                
                # Check if expired
                if conn.is_expired(self.config.max_lifetime):
                    logger.info(
                        f"Removing expired connection from pool {self.data_source_id}"
                    )
                    to_remove.append(conn)
                    continue
                
                # Check if idle too long (but keep minimum connections)
                if conn.is_idle_too_long(self.config.max_idle_time):
                    logger.info(
                        f"Removing idle connection from pool {self.data_source_id}"
                    )
                    to_remove.append(conn)
            
            # Remove connections
            for conn in to_remove:
                await self._remove_connection(conn)
                
                # Remove from available queue if present
                # Note: This is a simplified approach; in production you might want
                # a more sophisticated queue management
            
            if to_remove:
                logger.info(
                    f"Cleaned up {len(to_remove)} connections from pool {self.data_source_id} "
                    f"(remaining={len(self._connections)})"
                )


class ConnectionPoolManager:
    """Manages connection pools for multiple data sources
    
    This class provides a centralized way to manage connection pools for
    all registered data sources. It creates pools on-demand and handles
    their lifecycle.
    
    Attributes:
        _pools: Dictionary mapping data source IDs to connection pools
        _default_config: Default configuration for new pools
        _lock: Lock for thread-safe operations
    """
    
    def __init__(self, default_config: Optional[PoolConfig] = None):
        """Initialize the connection pool manager
        
        Args:
            default_config: Default configuration for pools
        """
        self._pools: Dict[str, ConnectionPool] = {}
        self._default_config = default_config or PoolConfig()
        self._lock = asyncio.Lock()
        
        logger.info("Connection pool manager initialized")
    
    async def get_pool(
        self,
        data_source_id: str,
        connector_factory,
        config: Optional[PoolConfig] = None
    ) -> ConnectionPool:
        """Get or create a connection pool for a data source
        
        Args:
            data_source_id: ID of the data source
            connector_factory: Factory function to create connectors
            config: Pool configuration (uses default if None)
            
        Returns:
            ConnectionPool instance
        """
        async with self._lock:
            if data_source_id not in self._pools:
                pool_config = config or self._default_config
                pool = ConnectionPool(data_source_id, connector_factory, pool_config)
                await pool.initialize()
                self._pools[data_source_id] = pool
                
                logger.info(f"Created connection pool for {data_source_id}")
            
            return self._pools[data_source_id]
    
    async def close_pool(self, data_source_id: str) -> None:
        """Close and remove a connection pool
        
        Args:
            data_source_id: ID of the data source
        """
        async with self._lock:
            if data_source_id in self._pools:
                pool = self._pools[data_source_id]
                await pool.close()
                del self._pools[data_source_id]
                
                logger.info(f"Closed connection pool for {data_source_id}")
    
    async def close_all(self) -> None:
        """Close all connection pools"""
        async with self._lock:
            for data_source_id, pool in self._pools.items():
                try:
                    await pool.close()
                    logger.info(f"Closed pool for {data_source_id}")
                except Exception as e:
                    logger.error(f"Error closing pool for {data_source_id}: {e}")
            
            self._pools.clear()
            logger.info("All connection pools closed")
    
    def get_pool_stats(self, data_source_id: str) -> Optional[Dict[str, int]]:
        """Get statistics for a connection pool
        
        Args:
            data_source_id: ID of the data source
            
        Returns:
            Dictionary with pool statistics or None if pool doesn't exist
        """
        if data_source_id not in self._pools:
            return None
        
        pool = self._pools[data_source_id]
        return {
            "total": pool.size(),
            "available": pool.available_count(),
            "in_use": pool.in_use_count(),
            "max_size": pool.config.max_size,
            "min_size": pool.config.min_size,
        }
    
    def list_pools(self) -> list[str]:
        """List all active pool IDs
        
        Returns:
            List of data source IDs with active pools
        """
        return list(self._pools.keys())
