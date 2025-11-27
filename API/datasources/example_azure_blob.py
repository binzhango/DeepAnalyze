"""
Example usage of Azure Blob Storage connector with DataSourceRegistry
Demonstrates how to register, connect, and use Azure Blob Storage
"""

import asyncio
import os
from API.datasources import (
    DataSourceRegistry,
    DataSourceConfig,
    DataSourceType,
    AzureBlobConnector,
)


async def main():
    """Example usage of Azure Blob Storage connector"""
    
    # Initialize registry
    registry = DataSourceRegistry()
    
    # Register the Azure Blob connector class
    registry.register_connector_class(DataSourceType.AZURE_BLOB, AzureBlobConnector)
    
    # Create configuration for Azure Blob Storage
    # Option 1: Using connection string
    config = DataSourceConfig(
        id="azure-blob-1",
        type=DataSourceType.AZURE_BLOB,
        name="My Azure Blob Storage",
        config={
            "connection_string": os.getenv("AZURE_STORAGE_CONNECTION_STRING", 
                                          "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net"),
            "container_name": "my-container"
        },
        metadata={
            "description": "Production data storage",
            "region": "us-east-1"
        }
    )
    
    # Option 2: Using SAS token (alternative)
    # config = DataSourceConfig(
    #     id="azure-blob-2",
    #     type=DataSourceType.AZURE_BLOB,
    #     name="My Azure Blob Storage (SAS)",
    #     config={
    #         "account_url": "https://myaccount.blob.core.windows.net",
    #         "sas_token": "sv=2020-08-04&ss=b&srt=sco&sp=rwdlac&se=2024-12-31T23:59:59Z",
    #         "container_name": "my-container"
    #     }
    # )
    
    try:
        # Register the data source (with connection test)
        print("Registering Azure Blob Storage data source...")
        data_source_id = await registry.register_data_source(config, test_connection=False)
        print(f"✓ Registered data source: {data_source_id}")
        
        # Get connector
        print("\nGetting connector...")
        connector = await registry.get_connector(data_source_id)
        print("✓ Connected to Azure Blob Storage")
        
        # List blobs in container
        print("\nListing blobs...")
        items = await connector.list_items()
        print(f"Found {len(items)} blobs:")
        for item in items[:5]:  # Show first 5
            print(f"  - {item.name} ({item.size} bytes)")
        
        # List blobs with prefix
        print("\nListing blobs with prefix 'data/'...")
        items = await connector.list_items(path="data/")
        print(f"Found {len(items)} blobs in 'data/' folder")
        
        # Get metadata for a specific blob
        if items:
            blob_path = items[0].path
            print(f"\nGetting metadata for '{blob_path}'...")
            metadata = await connector.get_metadata(blob_path)
            print(f"  Size: {metadata['size']} bytes")
            print(f"  Content Type: {metadata['content_type']}")
            print(f"  Last Modified: {metadata['last_modified']}")
        
        # Download a blob
        if items:
            blob_path = items[0].path
            workspace = "/tmp/azure_test"
            print(f"\nDownloading '{blob_path}' to workspace...")
            local_path = await connector.fetch_data(blob_path, workspace)
            print(f"✓ Downloaded to: {local_path}")
        
        # Upload a file
        print("\nUploading a test file...")
        test_file = "/tmp/test_upload.txt"
        with open(test_file, 'w') as f:
            f.write("This is a test file for Azure Blob Storage")
        
        blob_name = await connector.upload_file(test_file, blob_name="uploads/test.txt")
        print(f"✓ Uploaded as: {blob_name}")
        
        # Clean up
        os.remove(test_file)
        
        # List all registered data sources
        print("\nListing all registered data sources...")
        all_sources = registry.list_data_sources()
        for source in all_sources:
            print(f"  - {source.name} ({source.type.value})")
        
        # Get sanitized config (credentials hidden)
        print("\nGetting sanitized config...")
        sanitized_config = registry.get_config(data_source_id, sanitize=True)
        print(f"  Config: {sanitized_config.config}")
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    
    finally:
        # Disconnect all
        print("\nDisconnecting all connectors...")
        await registry.disconnect_all()
        print("✓ Done")


if __name__ == "__main__":
    asyncio.run(main())

