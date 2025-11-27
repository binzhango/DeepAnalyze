"""
Base connector interface for data sources
Defines abstract base class and common data structures for all data source connectors
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import time


class DataSourceType(Enum):
    """Enumeration of supported data source types"""
    AZURE_BLOB = "azure_blob"
    POSTGRESQL = "postgresql"
    LOCAL_FILE = "local_file"


@dataclass
class DataSourceConfig:
    """Configuration for a data source connection
    
    Attributes:
        id: Unique identifier for the data source
        type: Type of data source (Azure Blob, PostgreSQL, etc.)
        name: Human-readable name for the data source
        config: Type-specific configuration parameters (connection strings, credentials, etc.)
        created_at: Unix timestamp when the data source was created
        metadata: Additional metadata for the data source
    """
    id: str
    type: DataSourceType
    name: str
    config: Dict[str, Any]
    created_at: int = field(default_factory=lambda: int(time.time()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "config": self.config,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataSourceConfig":
        """Create from dictionary representation"""
        return cls(
            id=data["id"],
            type=DataSourceType(data["type"]),
            name=data["name"],
            config=data["config"],
            created_at=data.get("created_at", int(time.time())),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DataItem:
    """Represents an item in a data source (file, table, etc.)
    
    Attributes:
        name: Name of the item
        path: Full path or identifier for the item
        size: Size in bytes (0 for non-file items like database tables)
        modified_at: Unix timestamp of last modification
        metadata: Additional metadata specific to the item type
    """
    name: str
    path: str
    size: int
    modified_at: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "name": self.name,
            "path": self.path,
            "size": self.size,
            "modified_at": self.modified_at,
            "metadata": self.metadata,
        }


class DataSourceError(Exception):
    """Base exception for data source errors"""
    pass


class ConnectionError(DataSourceError):
    """Exception raised when connection to data source fails"""
    pass


class AuthenticationError(DataSourceError):
    """Exception raised when authentication fails"""
    pass


class DataFetchError(DataSourceError):
    """Exception raised when data fetching fails"""
    pass


class DataSourceConnector(ABC):
    """Abstract base class for all data source connectors
    
    This class defines the interface that all data source connectors must implement.
    Connectors provide a unified way to interact with different data sources like
    Azure Blob Storage, PostgreSQL databases, etc.
    
    Attributes:
        config: Configuration for this data source
        _connection: Internal connection object (implementation-specific)
    """
    
    def __init__(self, config: DataSourceConfig):
        """Initialize the connector with configuration
        
        Args:
            config: Data source configuration
        """
        self.config = config
        self._connection = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the data source
        
        This method should authenticate and establish a connection to the data source.
        It should handle connection pooling if applicable.
        
        Returns:
            True if connection successful, False otherwise
            
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the data source
        
        This method should properly close connections and clean up resources.
        It should be safe to call multiple times.
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the connection is valid and working
        
        This method should verify that the connection is active and the
        credentials are valid without performing expensive operations.
        
        Returns:
            True if connection is valid, False otherwise
        """
        pass
    
    @abstractmethod
    async def list_items(self, path: Optional[str] = None) -> List[DataItem]:
        """List available items in the data source
        
        For file-based sources (Azure Blob), this lists files/blobs.
        For databases (PostgreSQL), this lists tables/views.
        
        Args:
            path: Optional path to list items from (e.g., folder path, schema name)
            
        Returns:
            List of DataItem objects representing available items
            
        Raises:
            DataFetchError: If listing fails
        """
        pass
    
    @abstractmethod
    async def fetch_data(
        self, 
        identifier: str, 
        workspace: str
    ) -> str:
        """Fetch data from the source and save to workspace
        
        This method retrieves data from the source and saves it to the specified
        workspace directory. For files, it downloads them. For databases, it
        executes queries and saves results as CSV.
        
        Args:
            identifier: Identifier for the data to fetch (blob path, SQL query, etc.)
            workspace: Local workspace directory path where data should be saved
            
        Returns:
            Local file path where the data was saved
            
        Raises:
            DataFetchError: If fetching or saving fails
        """
        pass
    
    @abstractmethod
    async def get_metadata(self, identifier: str) -> Dict[str, Any]:
        """Get metadata for a specific item
        
        Returns detailed metadata about an item without fetching the full data.
        For files: size, content type, last modified, etc.
        For tables: schema, row count, column info, etc.
        
        Args:
            identifier: Identifier for the item
            
        Returns:
            Dictionary containing metadata
            
        Raises:
            DataFetchError: If metadata retrieval fails
        """
        pass
    
    def is_connected(self) -> bool:
        """Check if connector has an active connection
        
        Returns:
            True if connection exists, False otherwise
        """
        return self._connection is not None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
