"""
Data source connectors for DeepAnalyze API
Provides extensible plugin-based architecture for external data sources
"""

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
from .credentials import (
    CredentialManager,
    CredentialError,
)
from .registry import (
    DataSourceRegistry,
    RegistryError,
)
from .pool import (
    ConnectionPool,
    ConnectionPoolManager,
    PoolConfig,
    PooledConnection,
    PoolError,
)
from .azure_blob import (
    AzureBlobConnector,
)

__all__ = [
    "DataSourceType",
    "DataSourceConfig",
    "DataItem",
    "DataSourceConnector",
    "DataSourceError",
    "ConnectionError",
    "AuthenticationError",
    "DataFetchError",
    "CredentialManager",
    "CredentialError",
    "DataSourceRegistry",
    "RegistryError",
    "ConnectionPool",
    "ConnectionPoolManager",
    "PoolConfig",
    "PooledConnection",
    "PoolError",
    "AzureBlobConnector",
]
