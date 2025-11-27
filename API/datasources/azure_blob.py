"""
Azure Blob Storage Connector
Implements data source connector for Azure Blob Storage
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import (
    AzureError,
    ResourceNotFoundError,
    ClientAuthenticationError,
    HttpResponseError
)

from .base import (
    DataSourceConnector,
    DataSourceConfig,
    DataItem,
    ConnectionError as DSConnectionError,
    AuthenticationError,
    DataFetchError,
)

logger = logging.getLogger(__name__)


class AzureBlobConnector(DataSourceConnector):
    """Connector for Azure Blob Storage
    
    This connector provides access to Azure Blob Storage containers, allowing
    listing, downloading, and uploading of blobs.
    
    Configuration parameters:
        - connection_string: Azure Storage connection string (required if not using SAS)
        - account_url: Azure Storage account URL (required if using SAS token)
        - sas_token: Shared Access Signature token (optional)
        - container_name: Name of the container to access (required)
    
    Attributes:
        _blob_service_client: Azure BlobServiceClient instance
        _container_client: Azure ContainerClient instance
    """
    
    def __init__(self, config: DataSourceConfig):
        """Initialize Azure Blob connector
        
        Args:
            config: Data source configuration
        """
        super().__init__(config)
        self._blob_service_client: Optional[BlobServiceClient] = None
        self._container_client: Optional[ContainerClient] = None
    
    async def connect(self) -> bool:
        """Establish connection to Azure Blob Storage
        
        Returns:
            True if connection successful
            
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        try:
            # Get configuration parameters
            connection_string = self.config.config.get('connection_string')
            account_url = self.config.config.get('account_url')
            sas_token = self.config.config.get('sas_token')
            container_name = self.config.config.get('container_name')
            
            # Validate required parameters
            if not container_name:
                raise DSConnectionError("container_name is required in configuration")
            
            # Create BlobServiceClient based on available credentials
            if connection_string:
                self._blob_service_client = BlobServiceClient.from_connection_string(
                    connection_string
                )
                logger.info("Connected to Azure Blob Storage using connection string")
            elif account_url and sas_token:
                self._blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=sas_token
                )
                logger.info("Connected to Azure Blob Storage using SAS token")
            elif account_url:
                # Try without credentials (for public containers)
                self._blob_service_client = BlobServiceClient(account_url=account_url)
                logger.info("Connected to Azure Blob Storage without credentials")
            else:
                raise DSConnectionError(
                    "Either connection_string or account_url must be provided"
                )
            
            # Get container client
            self._container_client = self._blob_service_client.get_container_client(
                container_name
            )
            
            # Test connection by checking if container exists
            # Azure SDK's exists() is synchronous
            if not self._container_client.exists():
                raise DSConnectionError(
                    f"Container '{container_name}' does not exist or is not accessible"
                )
            
            self._connection = self._container_client
            logger.info(f"Successfully connected to container: {container_name}")
            return True
            
        except ClientAuthenticationError as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise AuthenticationError(
                f"Failed to authenticate with Azure Blob Storage: {str(e)}"
            ) from e
        except AzureError as e:
            logger.error(f"Azure connection error: {str(e)}")
            raise DSConnectionError(
                f"Failed to connect to Azure Blob Storage: {str(e)}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during connection: {str(e)}")
            raise DSConnectionError(
                f"Unexpected error connecting to Azure Blob Storage: {str(e)}"
            ) from e
    
    async def disconnect(self) -> None:
        """Close connection to Azure Blob Storage
        
        Azure SDK manages connections automatically, so this mainly cleans up references.
        """
        if self._blob_service_client:
            try:
                await self._blob_service_client.close()
            except Exception as e:
                logger.warning(f"Error closing blob service client: {str(e)}")
        
        self._blob_service_client = None
        self._container_client = None
        self._connection = None
        logger.info("Disconnected from Azure Blob Storage")
    
    async def test_connection(self) -> bool:
        """Test if the connection is valid
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Try to connect if not already connected
            if not self.is_connected():
                await self.connect()
            
            # Test by checking if container exists
            if self._container_client:
                # exists() is synchronous in Azure SDK
                return self._container_client.exists()
            
            return False
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

    async def list_items(self, path: Optional[str] = None) -> List[DataItem]:
        """List blobs in the container
        
        Args:
            path: Optional prefix to filter blobs (e.g., 'folder/')
            
        Returns:
            List of DataItem objects representing blobs
            
        Raises:
            DataFetchError: If listing fails
        """
        if not self.is_connected():
            raise DataFetchError("Not connected to Azure Blob Storage")
        
        try:
            items = []
            
            # List blobs with optional prefix
            blob_list = self._container_client.list_blobs(name_starts_with=path)
            
            async for blob in blob_list:
                # Extract blob name and metadata
                item = DataItem(
                    name=os.path.basename(blob.name),
                    path=blob.name,
                    size=blob.size,
                    modified_at=int(blob.last_modified.timestamp()),
                    metadata={
                        'content_type': blob.content_settings.content_type if blob.content_settings else None,
                        'etag': blob.etag,
                        'blob_type': blob.blob_type,
                    }
                )
                items.append(item)
            
            logger.info(f"Listed {len(items)} blobs from container")
            return items
            
        except AzureError as e:
            logger.error(f"Failed to list blobs: {str(e)}")
            raise DataFetchError(f"Failed to list blobs: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error listing blobs: {str(e)}")
            raise DataFetchError(f"Unexpected error listing blobs: {str(e)}") from e
    
    async def fetch_data(
        self, 
        identifier: str, 
        workspace: str
    ) -> str:
        """Download a blob to the workspace
        
        Args:
            identifier: Blob name/path to download
            workspace: Local workspace directory path
            
        Returns:
            Local file path where the blob was saved
            
        Raises:
            DataFetchError: If download fails
        """
        if not self.is_connected():
            raise DataFetchError("Not connected to Azure Blob Storage")
        
        try:
            # Get blob client
            blob_client = self._container_client.get_blob_client(identifier)
            
            # Check if blob exists
            if not await blob_client.exists():
                raise DataFetchError(f"Blob '{identifier}' does not exist")
            
            # Preserve original filename
            filename = os.path.basename(identifier)
            local_path = os.path.join(workspace, filename)
            
            # Ensure workspace directory exists
            os.makedirs(workspace, exist_ok=True)
            
            # Download blob to file
            with open(local_path, 'wb') as file:
                download_stream = await blob_client.download_blob()
                data = await download_stream.readall()
                file.write(data)
            
            logger.info(f"Downloaded blob '{identifier}' to '{local_path}'")
            return local_path
            
        except ResourceNotFoundError as e:
            logger.error(f"Blob not found: {identifier}")
            raise DataFetchError(f"Blob '{identifier}' not found: {str(e)}") from e
        except AzureError as e:
            logger.error(f"Failed to download blob '{identifier}': {str(e)}")
            raise DataFetchError(
                f"Failed to download blob '{identifier}': {str(e)}"
            ) from e
        except OSError as e:
            logger.error(f"Failed to write file to workspace: {str(e)}")
            raise DataFetchError(
                f"Failed to write file to workspace: {str(e)}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error downloading blob: {str(e)}")
            raise DataFetchError(
                f"Unexpected error downloading blob '{identifier}': {str(e)}"
            ) from e
    
    async def get_metadata(self, identifier: str) -> Dict[str, Any]:
        """Get metadata for a specific blob
        
        Args:
            identifier: Blob name/path
            
        Returns:
            Dictionary containing blob metadata
            
        Raises:
            DataFetchError: If metadata retrieval fails
        """
        if not self.is_connected():
            raise DataFetchError("Not connected to Azure Blob Storage")
        
        try:
            # Get blob client
            blob_client = self._container_client.get_blob_client(identifier)
            
            # Get blob properties
            properties = await blob_client.get_blob_properties()
            
            metadata = {
                'name': identifier,
                'size': properties.size,
                'content_type': properties.content_settings.content_type,
                'last_modified': int(properties.last_modified.timestamp()),
                'etag': properties.etag,
                'blob_type': properties.blob_type,
                'creation_time': int(properties.creation_time.timestamp()) if properties.creation_time else None,
                'metadata': properties.metadata,
            }
            
            logger.info(f"Retrieved metadata for blob: {identifier}")
            return metadata
            
        except ResourceNotFoundError as e:
            logger.error(f"Blob not found: {identifier}")
            raise DataFetchError(f"Blob '{identifier}' not found: {str(e)}") from e
        except AzureError as e:
            logger.error(f"Failed to get metadata for blob '{identifier}': {str(e)}")
            raise DataFetchError(
                f"Failed to get metadata for blob '{identifier}': {str(e)}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error getting metadata: {str(e)}")
            raise DataFetchError(
                f"Unexpected error getting metadata for blob '{identifier}': {str(e)}"
            ) from e
    
    async def upload_file(
        self,
        local_path: str,
        blob_name: Optional[str] = None,
        overwrite: bool = True
    ) -> str:
        """Upload a file to Azure Blob Storage
        
        This is an additional method specific to Azure Blob Storage for uploading
        analysis results back to the cloud.
        
        Args:
            local_path: Path to local file to upload
            blob_name: Name for the blob (if None, uses filename from local_path)
            overwrite: Whether to overwrite existing blob
            
        Returns:
            Blob name/path of uploaded file
            
        Raises:
            DataFetchError: If upload fails
        """
        if not self.is_connected():
            raise DataFetchError("Not connected to Azure Blob Storage")
        
        try:
            # Validate local file exists
            if not os.path.exists(local_path):
                raise DataFetchError(f"Local file '{local_path}' does not exist")
            
            # Use filename if blob_name not provided
            if blob_name is None:
                blob_name = os.path.basename(local_path)
            
            # Get blob client
            blob_client = self._container_client.get_blob_client(blob_name)
            
            # Upload file
            with open(local_path, 'rb') as file:
                await blob_client.upload_blob(file, overwrite=overwrite)
            
            logger.info(f"Uploaded file '{local_path}' to blob '{blob_name}'")
            return blob_name
            
        except FileNotFoundError as e:
            logger.error(f"Local file not found: {local_path}")
            raise DataFetchError(f"Local file '{local_path}' not found") from e
        except AzureError as e:
            logger.error(f"Failed to upload file '{local_path}': {str(e)}")
            raise DataFetchError(
                f"Failed to upload file '{local_path}': {str(e)}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {str(e)}")
            raise DataFetchError(
                f"Unexpected error uploading file '{local_path}': {str(e)}"
            ) from e
