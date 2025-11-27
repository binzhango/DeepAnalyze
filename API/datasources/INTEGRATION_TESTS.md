# Integration Tests for Azure Blob Storage Connector

## Overview

Integration tests validate the Azure Blob Storage connector against real Azure Blob Storage or the Azurite emulator. These tests ensure that the connector works correctly with actual Azure services, not just mocked responses.

## Test Coverage

The integration tests cover:

1. **Connection Management**
   - Connecting to Azure Blob Storage
   - Testing connection validity
   - Using connector as async context manager
   - Proper disconnection

2. **Blob Operations**
   - Listing blobs (with and without prefix)
   - Uploading files
   - Downloading blobs
   - Getting blob metadata
   - Overwriting existing blobs

3. **Error Handling**
   - Fetching nonexistent blobs
   - Getting metadata for nonexistent blobs

4. **Round Trip Testing**
   - Upload → Download → Verify content matches

5. **Multiple Operations**
   - Sequential operations to test state management

## Running Integration Tests

### Option 1: Using Azurite Emulator (Recommended)

Azurite is a local Azure Storage emulator that's perfect for testing without needing real Azure credentials.

#### 1. Start Azurite

Using Docker:
```bash
docker run -p 10000:10000 mcr.microsoft.com/azure-storage/azurite \
  azurite-blob --blobHost 0.0.0.0
```

Or install and run locally:
```bash
npm install -g azurite
azurite --silent --location /tmp/azurite --debug /tmp/azurite/debug.log
```

#### 2. Run Tests

```bash
# Run all integration tests
pytest API/datasources/test_azure_blob_integration.py -v

# Run with output
pytest API/datasources/test_azure_blob_integration.py -v -s

# Run specific test
pytest API/datasources/test_azure_blob_integration.py::test_integration_upload_and_download_roundtrip -v
```

### Option 2: Using Real Azure Blob Storage

If you have an Azure Storage account, you can test against real Azure.

#### 1. Set Environment Variables

```bash
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net"
export AZURE_STORAGE_CONTAINER_NAME="test-container"
```

#### 2. Create Test Container

Make sure the container exists in your Azure Storage account:
```bash
az storage container create --name test-container --connection-string "$AZURE_STORAGE_CONNECTION_STRING"
```

#### 3. Run Tests

```bash
pytest API/datasources/test_azure_blob_integration.py -v
```

## Test Behavior

### When Azure is Available

Tests will:
- Connect to Azure Blob Storage or Azurite
- Create test blobs
- Perform operations
- Clean up test data
- Report results

### When Azure is Not Available

Tests will:
- Automatically skip with message: "Azure Blob Storage or Azurite not available"
- Not fail the test suite
- Allow unit tests to run independently

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      azurite:
        image: mcr.microsoft.com/azure-storage/azurite
        ports:
          - 10000:10000
        options: >-
          --health-cmd "nc -z localhost 10000"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio
      
      - name: Run integration tests
        run: |
          pytest API/datasources/test_azure_blob_integration.py -v
```

### GitLab CI Example

```yaml
integration-tests:
  image: python:3.9
  
  services:
    - name: mcr.microsoft.com/azure-storage/azurite
      alias: azurite
      command: ["azurite-blob", "--blobHost", "0.0.0.0"]
  
  variables:
    AZURE_STORAGE_CONNECTION_STRING: "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://azurite:10000/devstoreaccount1;"
  
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-asyncio
    - pytest API/datasources/test_azure_blob_integration.py -v
```

## Troubleshooting

### Tests Skip Immediately

**Problem**: All tests skip with "Azure Blob Storage or Azurite not available"

**Solutions**:
1. Check if Azurite is running: `curl http://localhost:10000`
2. Verify connection string is correct
3. Check firewall/network settings
4. Try running Azurite with `--blobHost 0.0.0.0`

### Connection Timeout

**Problem**: Tests hang or timeout when connecting

**Solutions**:
1. Increase timeout in pytest: `pytest --timeout=60`
2. Check if Azurite is accessible: `nc -zv localhost 10000`
3. Verify no other service is using port 10000

### Container Already Exists Error

**Problem**: Tests fail because container already exists

**Solution**: Tests automatically handle this - they create the container if it doesn't exist. If you see this error, it's likely a permissions issue.

### Authentication Errors with Real Azure

**Problem**: "Authentication failed" errors

**Solutions**:
1. Verify connection string is correct
2. Check if account key is valid
3. Ensure container exists and you have permissions
4. Try regenerating the account key in Azure Portal

## Test Data Cleanup

Integration tests automatically clean up test data:
- Test blobs are deleted after each test
- Temporary files are removed
- Connections are properly closed

If tests are interrupted, you may need to manually clean up:

```bash
# List blobs in test container
az storage blob list --container-name test-container --connection-string "$AZURE_STORAGE_CONNECTION_STRING"

# Delete test blobs
az storage blob delete-batch --source test-container --pattern "integration-test/*" --connection-string "$AZURE_STORAGE_CONNECTION_STRING"
```

## Performance Considerations

Integration tests are slower than unit tests because they:
- Make real network calls
- Upload/download actual data
- Wait for Azure operations to complete

Typical execution times:
- With Azurite (local): 5-10 seconds
- With real Azure: 15-30 seconds (depends on network)

## Best Practices

1. **Run unit tests first**: They're faster and catch most issues
2. **Use Azurite for development**: Faster and doesn't require Azure credentials
3. **Test against real Azure before deployment**: Ensures compatibility
4. **Keep test data small**: Use small files to speed up tests
5. **Clean up after tests**: Prevent accumulation of test data

## Adding New Integration Tests

When adding new integration tests:

1. Use the `azure_connector` fixture for connection management
2. Use the `test_blob` fixture if you need a pre-existing blob
3. Clean up any test data you create
4. Add descriptive print statements for debugging
5. Handle both success and error cases

Example:
```python
@pytest.mark.asyncio
async def test_integration_my_new_feature(azure_connector):
    """Test description"""
    # Your test code here
    result = await azure_connector.my_new_method()
    assert result is not None
    print("✓ My new feature works")
```

## Related Documentation

- [Azure Blob Storage Connector](./azure_blob.py)
- [Unit Tests](./test_azure_blob.py)
- [Example Usage](./example_azure_blob.py)
- [Azurite Documentation](https://github.com/Azure/Azurite)
