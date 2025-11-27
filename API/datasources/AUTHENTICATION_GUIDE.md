# Azure Blob Storage Authentication Guide

## Overview

The Azure Blob Storage connector supports multiple authentication methods to provide flexibility for different security requirements and use cases. This guide explains each method, when to use it, and how to configure it properly.

## Authentication Methods

### 1. Connection String Authentication (Recommended for Development)

**What it is:** A connection string contains all the information needed to connect to your Azure Storage account, including the account name, account key, and endpoint.

**When to use:**
- Development and testing environments
- When you have full access to the storage account
- When you need read and write permissions
- Internal applications with secure credential storage

**Security Level:** 🔴 High privilege - Full access to storage account

**Configuration:**

```python
from API.datasources import DataSourceConfig, DataSourceType

config = DataSourceConfig(
    id="azure-blob-conn-string",
    type=DataSourceType.AZURE_BLOB,
    name="Azure Storage (Connection String)",
    config={
        "connection_string": "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey==;EndpointSuffix=core.windows.net",
        "container_name": "my-container"
    }
)
```

**How to get your connection string:**

1. Go to Azure Portal
2. Navigate to your Storage Account
3. Click "Access keys" in the left menu
4. Copy "Connection string" from key1 or key2

**Best Practices:**
- ✅ Store in environment variables: `os.getenv("AZURE_STORAGE_CONNECTION_STRING")`
- ✅ Use Azure Key Vault for production
- ✅ Rotate keys regularly
- ❌ Never commit to version control
- ❌ Never log or display in plain text

---

### 2. SAS Token Authentication (Recommended for Production)

**What it is:** A Shared Access Signature (SAS) token provides delegated access to resources with specific permissions and time limits.

**When to use:**
- Production environments
- When you need time-limited access
- When you want to grant specific permissions (read-only, write-only, etc.)
- Sharing access with external parties
- Implementing least-privilege security

**Security Level:** 🟡 Configurable - Limited by token permissions and expiration

**Configuration:**

```python
config = DataSourceConfig(
    id="azure-blob-sas",
    type=DataSourceType.AZURE_BLOB,
    name="Azure Storage (SAS Token)",
    config={
        "account_url": "https://myaccount.blob.core.windows.net",
        "sas_token": "sv=2020-08-04&ss=b&srt=sco&sp=rwdlac&se=2024-12-31T23:59:59Z&st=2024-01-01T00:00:00Z&spr=https&sig=signature",
        "container_name": "my-container"
    }
)
```

**How to generate a SAS token:**

#### Option A: Azure Portal (Container-level SAS)

1. Go to Azure Portal
2. Navigate to your Storage Account
3. Go to "Containers" and select your container
4. Click "Shared access tokens" in the left menu
5. Configure permissions and expiration
6. Click "Generate SAS token and URL"
7. Copy the SAS token (without the leading `?`)

#### Option B: Azure CLI

```bash
# Generate container-level SAS token
az storage container generate-sas \
    --account-name myaccount \
    --name my-container \
    --permissions rl \
    --expiry 2024-12-31T23:59:59Z \
    --https-only \
    --output tsv
```

#### Option C: Python SDK

```python
from azure.storage.blob import BlobServiceClient, generate_container_sas, ContainerSasPermissions
from datetime import datetime, timedelta

# Create service client
service_client = BlobServiceClient.from_connection_string(connection_string)

# Generate SAS token
sas_token = generate_container_sas(
    account_name="myaccount",
    container_name="my-container",
    account_key="mykey==",
    permission=ContainerSasPermissions(read=True, list=True),
    expiry=datetime.utcnow() + timedelta(days=30),
    protocol="https"
)
```

**SAS Token Permissions:**

| Permission | Code | Description |
|------------|------|-------------|
| Read | `r` | Read blob content, metadata, and properties |
| Write | `w` | Write blob content, metadata, and properties |
| Delete | `d` | Delete blobs |
| List | `l` | List blobs in container |
| Add | `a` | Add blocks to append blobs |
| Create | `c` | Create new blobs |

**Common Permission Combinations:**

- **Read-only access:** `rl` (read + list)
- **Read-write access:** `rwl` (read + write + list)
- **Full access:** `rwdlac` (all permissions)

**Best Practices:**
- ✅ Use shortest expiration time needed
- ✅ Grant minimum required permissions
- ✅ Use HTTPS-only tokens
- ✅ Regenerate tokens before expiration
- ✅ Store in environment variables
- ✅ Monitor token usage
- ❌ Never use tokens without expiration
- ❌ Never grant more permissions than needed

---

### 3. Public Container Access (No Authentication)

**What it is:** Access to publicly accessible containers without any credentials.

**When to use:**
- Accessing public datasets
- Reading from containers with anonymous read access
- Testing with public data

**Security Level:** 🟢 No credentials - Public read-only access

**Configuration:**

```python
config = DataSourceConfig(
    id="azure-blob-public",
    type=DataSourceType.AZURE_BLOB,
    name="Azure Storage (Public)",
    config={
        "account_url": "https://myaccount.blob.core.windows.net",
        "container_name": "public-container"
    }
)
```

**Note:** The container must be configured for public access in Azure Portal.

**Best Practices:**
- ✅ Only use for truly public data
- ✅ Verify container is intentionally public
- ❌ Never store sensitive data in public containers

---

## Security Best Practices

### 1. Environment Variables

Store credentials in environment variables, not in code:

```python
import os

config = DataSourceConfig(
    id="azure-blob-1",
    type=DataSourceType.AZURE_BLOB,
    name="Azure Storage",
    config={
        "connection_string": os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        "container_name": os.getenv("AZURE_CONTAINER_NAME", "default-container")
    }
)
```

### 2. Azure Key Vault Integration

For production applications, use Azure Key Vault:

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Get credentials from Key Vault
credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://myvault.vault.azure.net/", credential=credential)
connection_string = client.get_secret("azure-storage-connection-string").value

config = DataSourceConfig(
    id="azure-blob-1",
    type=DataSourceType.AZURE_BLOB,
    name="Azure Storage",
    config={
        "connection_string": connection_string,
        "container_name": "my-container"
    }
)
```

### 3. Credential Rotation

Implement automatic credential rotation:

```python
import asyncio
from datetime import datetime, timedelta

async def rotate_credentials(registry, data_source_id):
    """Rotate SAS token before expiration"""
    while True:
        # Wait until 1 day before expiration
        await asyncio.sleep(timedelta(days=29).total_seconds())
        
        # Generate new SAS token
        new_token = generate_new_sas_token()
        
        # Update configuration
        config = registry.get_config(data_source_id)
        config.config["sas_token"] = new_token
        
        # Re-register with new credentials
        await registry.register_data_source(config)
```

### 4. Sanitize Configurations

Always sanitize configurations before logging or displaying:

```python
# Get sanitized config (credentials masked)
sanitized_config = registry.get_config("azure-blob-1", sanitize=True)
print(f"Config: {sanitized_config.config}")
# Output: {'connection_string': '***REDACTED***', 'container_name': 'my-container'}
```

### 5. Least Privilege Access

Always use the minimum permissions required:

```python
# For read-only analysis, use read-only SAS token
sas_token = generate_container_sas(
    account_name="myaccount",
    container_name="my-container",
    account_key="mykey==",
    permission=ContainerSasPermissions(read=True, list=True),  # Only read and list
    expiry=datetime.utcnow() + timedelta(hours=24),  # Short expiration
    protocol="https"
)
```

---

## Error Handling

### Authentication Errors

```python
from API.datasources import AuthenticationError, ConnectionError

try:
    connector = await registry.get_connector("azure-blob-1")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    # Possible causes:
    # - Invalid connection string or SAS token
    # - Expired SAS token
    # - Incorrect account key
    # - Token doesn't have required permissions
except ConnectionError as e:
    print(f"Connection failed: {e}")
    # Possible causes:
    # - Container doesn't exist
    # - Network connectivity issues
    # - Firewall blocking access
```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `AuthenticationError: Failed to authenticate` | Invalid credentials | Verify connection string or SAS token |
| `ConnectionError: Container does not exist` | Wrong container name | Check container name spelling |
| `AuthenticationError: Signature mismatch` | Incorrect account key | Regenerate connection string |
| `AuthenticationError: Token expired` | SAS token expired | Generate new SAS token |
| `AuthenticationError: Insufficient permissions` | SAS token lacks permissions | Generate token with required permissions |

---

## Testing Authentication

### Test Connection String

```python
import asyncio
from API.datasources import DataSourceRegistry, DataSourceConfig, DataSourceType, AzureBlobConnector

async def test_connection_string():
    registry = DataSourceRegistry()
    registry.register_connector_class(DataSourceType.AZURE_BLOB, AzureBlobConnector)
    
    config = DataSourceConfig(
        id="test-conn-string",
        type=DataSourceType.AZURE_BLOB,
        name="Test Connection String",
        config={
            "connection_string": "your-connection-string",
            "container_name": "test-container"
        }
    )
    
    try:
        # Test connection during registration
        await registry.register_data_source(config, test_connection=True)
        print("✓ Connection string authentication successful")
    except Exception as e:
        print(f"✗ Connection string authentication failed: {e}")

asyncio.run(test_connection_string())
```

### Test SAS Token

```python
async def test_sas_token():
    registry = DataSourceRegistry()
    registry.register_connector_class(DataSourceType.AZURE_BLOB, AzureBlobConnector)
    
    config = DataSourceConfig(
        id="test-sas",
        type=DataSourceType.AZURE_BLOB,
        name="Test SAS Token",
        config={
            "account_url": "https://myaccount.blob.core.windows.net",
            "sas_token": "your-sas-token",
            "container_name": "test-container"
        }
    )
    
    try:
        await registry.register_data_source(config, test_connection=True)
        print("✓ SAS token authentication successful")
    except Exception as e:
        print(f"✗ SAS token authentication failed: {e}")

asyncio.run(test_sas_token())
```

---

## Comparison Matrix

| Feature | Connection String | SAS Token | Public Access |
|---------|------------------|-----------|---------------|
| **Security** | High privilege | Configurable | No auth |
| **Expiration** | No expiration | Time-limited | N/A |
| **Permissions** | Full access | Granular | Read-only |
| **Rotation** | Manual | Automatic | N/A |
| **Use Case** | Development | Production | Public data |
| **Complexity** | Simple | Moderate | Simple |
| **Best For** | Internal apps | External sharing | Testing |

---

## Troubleshooting

### Issue: "Authentication failed"

**Symptoms:** `AuthenticationError` when connecting

**Checklist:**
1. ✓ Verify credentials are correct
2. ✓ Check for extra spaces or newlines in credentials
3. ✓ Ensure SAS token hasn't expired
4. ✓ Verify account name matches
5. ✓ Check that container name is correct
6. ✓ Test credentials in Azure Portal or Azure Storage Explorer

### Issue: "Container does not exist"

**Symptoms:** `ConnectionError: Container 'name' does not exist`

**Checklist:**
1. ✓ Verify container name spelling (case-sensitive)
2. ✓ Check that container exists in the storage account
3. ✓ Ensure credentials have access to the container
4. ✓ Verify you're using the correct storage account

### Issue: "Insufficient permissions"

**Symptoms:** Operations fail with permission errors

**Checklist:**
1. ✓ Check SAS token permissions
2. ✓ Verify token includes required permissions (r, l, w, etc.)
3. ✓ Ensure token is for the correct resource (container vs blob)
4. ✓ Check that token hasn't expired

---

## Additional Resources

- [Azure Storage Authentication Documentation](https://docs.microsoft.com/en-us/azure/storage/common/storage-auth)
- [SAS Token Best Practices](https://docs.microsoft.com/en-us/azure/storage/common/storage-sas-overview)
- [Azure Key Vault Integration](https://docs.microsoft.com/en-us/azure/key-vault/)
- [Azure Storage Security Guide](https://docs.microsoft.com/en-us/azure/storage/common/storage-security-guide)

---

## Quick Reference

### Connection String Format
```
DefaultEndpointsProtocol=https;
AccountName=<account-name>;
AccountKey=<account-key>;
EndpointSuffix=core.windows.net
```

### SAS Token Format
```
sv=2020-08-04&ss=b&srt=sco&sp=rwdlac&se=2024-12-31T23:59:59Z&st=2024-01-01T00:00:00Z&spr=https&sig=<signature>
```

### Account URL Format
```
https://<account-name>.blob.core.windows.net
```
