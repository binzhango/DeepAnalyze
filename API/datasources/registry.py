"""
Data Source Registry
Manages registration, lifecycle, and access to data source connectors
"""

import asyncio
import logging
from typing import Dict, List, Optional, Type
from datetime import datetime, timedelta

from .base import (
    DataSourceConnector,
    DataSourceConfig,
    DataSourceType,
    DataSourceError,
    ConnectionError as DSConnectionError,
)
from .credentials import CredentialManager

logger = logging.getLogger(__name__)


class RegistryError(DataSourceError):
    """Exception raised for registry-specific errors"""
    pass


class DataSourceRegistry:
    """Central registry for managing data source connectors
    
    The registry provides:
    - Registration and storage of data source configurations
    - Connector factory pattern for creating connector instances
    - Connection lifecycle management
    - Metadata caching
    - Thread-safe access to connectors
    
    Attributes:
        _connectors: Dictionary mapping data source IDs to connector instances
        _configs: Dictionary mapping data source IDs to configurations
        _connector_classes: Dictionary mapping data source types to connector classes
        _credential_manager: Manager for encrypting/decrypting credentials
        _metadata_cache: Cache for data source metadata
        _cache_ttl: Time-to-live for cached metadata in seconds
        _lock: Asyncio lock for thread-safe operations
    """
    
    def __init__(
        self,
        credential_manager: Optional[CredentialManager] = None,
        cache_ttl: int = 300  # 5 minutes default
    ):
        """Initialize the data source registry
        
        Args:
            credential_manager: Manager for credential encryption. If None, creates new one.
            cache_ttl: Time-to-live for metadata cache in seconds
        """
        self._connectors: Dict[str, DataSourceConnector] = {}
        self._configs: Dict[str, DataSourceConfig] = {}
        self._connector_classes: Dict[DataSourceType, Type[DataSourceConnector]] = {}
        self._credential_manager = credential_manager or CredentialManager()
        self._metadata_cache: Dict[str, tuple[datetime, Dict]] = {}
        self._cache_ttl = cache_ttl
        self._lock = asyncio.Lock()
        
        logger.info("Data source registry initialized")
    
    def register_connector_class(
        self,
        data_source_type: DataSourceType,
        connector_class: Type[DataSourceConnector]
    ) -> None:
        """Register a connector class for a data source type
        
        This allows the registry to create connector instances for specific
        data source types using the factory pattern.
        
        Args:
            data_source_type: Type of data source (e.g., AZURE_BLOB, POSTGRESQL)
            connector_class: Class that implements DataSourceConnector interface
        
        Raises:
            RegistryError: If connector class is already registered for this type
        """
        if data_source_type in self._connector_classes:
            logger.warning(
                f"Connector class for {data_source_type.value} already registered. "
                "Overwriting with new class."
            )
        
        self._connector_classes[data_source_type] = connector_class
        logger.info(f"Registered connector class for {data_source_type.value}")
    
    async def register_data_source(
        self,
        config: DataSourceConfig,
        test_connection: bool = True
    ) -> str:
        """Register a new data source
        
        Args:
            config: Configuration for the data source
            test_connection: Whether to test the connection before registering
        
        Returns:
            ID of the registered data source
        
        Raises:
            RegistryError: If data source type is not supported or ID already exists
            ConnectionError: If test_connection is True and connection fails
        """
        async with self._lock:
            # Check if connector class is registered for this type
            if config.type not in self._connector_classes:
                raise RegistryError(
                    f"No connector class registered for type: {config.type.value}"
                )
            
            # Check if ID already exists
            if config.id in self._configs:
                raise RegistryError(
                    f"Data source with ID '{config.id}' already exists"
                )
            
            # Encrypt sensitive credentials in config
            encrypted_config = self._encrypt_config(config)
            
            # Test connection if requested
            if test_connection:
                connector = self._create_connector(encrypted_config)
                try:
                    success = await connector.test_connection()
                    if not success:
                        raise DSConnectionError(
                            f"Connection test failed for data source '{config.name}'"
                        )
                except Exception as e:
                    logger.error(f"Connection test failed: {str(e)}")
                    raise DSConnectionError(
                        f"Failed to connect to data source: {str(e)}"
                    ) from e
                finally:
                    await connector.disconnect()
            
            # Store configuration
            self._configs[config.id] = encrypted_config
            logger.info(f"Registered data source: {config.id} ({config.name})")
            
            return config.id
    
    async def unregister_data_source(self, data_source_id: str) -> None:
        """Unregister and remove a data source
        
        This will disconnect any active connector and remove the configuration.
        
        Args:
            data_source_id: ID of the data source to remove
        
        Raises:
            RegistryError: If data source ID does not exist
        """
        async with self._lock:
            if data_source_id not in self._configs:
                raise RegistryError(
                    f"Data source with ID '{data_source_id}' not found"
                )
            
            # Disconnect if connector exists
            if data_source_id in self._connectors:
                connector = self._connectors[data_source_id]
                await connector.disconnect()
                del self._connectors[data_source_id]
            
            # Remove configuration
            del self._configs[data_source_id]
            
            # Clear cached metadata
            if data_source_id in self._metadata_cache:
                del self._metadata_cache[data_source_id]
            
            logger.info(f"Unregistered data source: {data_source_id}")
    
    async def get_connector(self, data_source_id: str) -> DataSourceConnector:
        """Get a connector instance for a data source
        
        If a connector already exists, returns it. Otherwise, creates a new one
        and establishes a connection.
        
        Args:
            data_source_id: ID of the data source
        
        Returns:
            Connected DataSourceConnector instance
        
        Raises:
            RegistryError: If data source ID does not exist
            ConnectionError: If connection fails
        """
        async with self._lock:
            if data_source_id not in self._configs:
                raise RegistryError(
                    f"Data source with ID '{data_source_id}' not found"
                )
            
            # Return existing connector if available and connected
            if data_source_id in self._connectors:
                connector = self._connectors[data_source_id]
                if connector.is_connected():
                    return connector
                else:
                    # Reconnect if disconnected
                    await connector.connect()
                    return connector
            
            # Create new connector
            config = self._configs[data_source_id]
            connector = self._create_connector(config)
            
            # Connect
            try:
                await connector.connect()
            except Exception as e:
                logger.error(f"Failed to connect to data source {data_source_id}: {str(e)}")
                raise DSConnectionError(
                    f"Failed to connect to data source: {str(e)}"
                ) from e
            
            # Store connector
            self._connectors[data_source_id] = connector
            logger.info(f"Created and connected connector for: {data_source_id}")
            
            return connector
    
    def get_config(
        self,
        data_source_id: str,
        decrypt: bool = False,
        sanitize: bool = True
    ) -> DataSourceConfig:
        """Get configuration for a data source
        
        Args:
            data_source_id: ID of the data source
            decrypt: Whether to decrypt credentials (use with caution)
            sanitize: Whether to sanitize sensitive fields (ignored if decrypt=True)
        
        Returns:
            DataSourceConfig object
        
        Raises:
            RegistryError: If data source ID does not exist
        """
        if data_source_id not in self._configs:
            raise RegistryError(
                f"Data source with ID '{data_source_id}' not found"
            )
        
        config = self._configs[data_source_id]
        
        if decrypt:
            return self._decrypt_config(config)
        elif sanitize:
            # First decrypt to get actual config, then sanitize
            decrypted_config = self._decrypt_config(config)
            sanitized_config = DataSourceConfig(
                id=decrypted_config.id,
                type=decrypted_config.type,
                name=decrypted_config.name,
                config=self._credential_manager.sanitize_config(decrypted_config.config),
                created_at=decrypted_config.created_at,
                metadata=decrypted_config.metadata
            )
            return sanitized_config
        else:
            return config
    
    def list_data_sources(self, sanitize: bool = True) -> List[DataSourceConfig]:
        """List all registered data sources
        
        Args:
            sanitize: Whether to sanitize sensitive fields in configs
        
        Returns:
            List of DataSourceConfig objects
        """
        configs = []
        for data_source_id in self._configs:
            config = self.get_config(data_source_id, decrypt=False, sanitize=sanitize)
            configs.append(config)
        
        return configs
    
    def exists(self, data_source_id: str) -> bool:
        """Check if a data source exists in the registry
        
        Args:
            data_source_id: ID of the data source
        
        Returns:
            True if data source exists, False otherwise
        """
        return data_source_id in self._configs
    
    async def test_connection(self, data_source_id: str) -> bool:
        """Test connection to a data source
        
        Args:
            data_source_id: ID of the data source
        
        Returns:
            True if connection successful, False otherwise
        
        Raises:
            RegistryError: If data source ID does not exist
        """
        if data_source_id not in self._configs:
            raise RegistryError(
                f"Data source with ID '{data_source_id}' not found"
            )
        
        config = self._configs[data_source_id]
        connector = self._create_connector(config)
        
        try:
            result = await connector.test_connection()
            return result
        except Exception as e:
            logger.error(f"Connection test failed for {data_source_id}: {str(e)}")
            return False
        finally:
            await connector.disconnect()
    
    async def disconnect_all(self) -> None:
        """Disconnect all active connectors
        
        This should be called during application shutdown to properly
        close all connections.
        """
        async with self._lock:
            for data_source_id, connector in self._connectors.items():
                try:
                    await connector.disconnect()
                    logger.info(f"Disconnected: {data_source_id}")
                except Exception as e:
                    logger.error(f"Error disconnecting {data_source_id}: {str(e)}")
            
            self._connectors.clear()
            logger.info("All connectors disconnected")
    
    def get_cached_metadata(self, data_source_id: str) -> Optional[Dict]:
        """Get cached metadata for a data source
        
        Args:
            data_source_id: ID of the data source
        
        Returns:
            Cached metadata dictionary or None if not cached or expired
        """
        if data_source_id not in self._metadata_cache:
            return None
        
        cached_time, metadata = self._metadata_cache[data_source_id]
        
        # Check if cache is expired
        if datetime.now() - cached_time > timedelta(seconds=self._cache_ttl):
            del self._metadata_cache[data_source_id]
            return None
        
        return metadata
    
    def cache_metadata(self, data_source_id: str, metadata: Dict) -> None:
        """Cache metadata for a data source
        
        Args:
            data_source_id: ID of the data source
            metadata: Metadata dictionary to cache
        """
        self._metadata_cache[data_source_id] = (datetime.now(), metadata)
    
    def clear_cache(self, data_source_id: Optional[str] = None) -> None:
        """Clear metadata cache
        
        Args:
            data_source_id: ID of specific data source to clear, or None to clear all
        """
        if data_source_id:
            if data_source_id in self._metadata_cache:
                del self._metadata_cache[data_source_id]
        else:
            self._metadata_cache.clear()
    
    def _create_connector(self, config: DataSourceConfig) -> DataSourceConnector:
        """Create a connector instance from configuration
        
        Args:
            config: Data source configuration
        
        Returns:
            DataSourceConnector instance
        
        Raises:
            RegistryError: If connector class not registered for type
        """
        if config.type not in self._connector_classes:
            raise RegistryError(
                f"No connector class registered for type: {config.type.value}"
            )
        
        connector_class = self._connector_classes[config.type]
        decrypted_config = self._decrypt_config(config)
        
        return connector_class(decrypted_config)
    
    def _encrypt_config(self, config: DataSourceConfig) -> DataSourceConfig:
        """Encrypt sensitive fields in configuration
        
        Args:
            config: Configuration with plaintext credentials
        
        Returns:
            Configuration with encrypted credentials
        """
        # Create a copy to avoid modifying original
        encrypted_config = DataSourceConfig(
            id=config.id,
            type=config.type,
            name=config.name,
            config=config.config.copy(),
            created_at=config.created_at,
            metadata=config.metadata.copy()
        )
        
        # Encrypt the entire config dict
        encrypted_str = self._credential_manager.encrypt_credentials(config.config)
        encrypted_config.config = {"_encrypted": encrypted_str}
        
        return encrypted_config
    
    def _decrypt_config(self, config: DataSourceConfig) -> DataSourceConfig:
        """Decrypt sensitive fields in configuration
        
        Args:
            config: Configuration with encrypted credentials
        
        Returns:
            Configuration with decrypted credentials
        """
        # Check if config is encrypted
        if "_encrypted" not in config.config:
            # Already decrypted or never encrypted
            return config
        
        # Decrypt
        encrypted_str = config.config["_encrypted"]
        decrypted_dict = self._credential_manager.decrypt_credentials(encrypted_str)
        
        # Create decrypted config
        decrypted_config = DataSourceConfig(
            id=config.id,
            type=config.type,
            name=config.name,
            config=decrypted_dict,
            created_at=config.created_at,
            metadata=config.metadata.copy()
        )
        
        return decrypted_config
