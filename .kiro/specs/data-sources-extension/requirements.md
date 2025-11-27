# Requirements Document: Azure Blob Storage and PostgreSQL Data Sources

## Introduction

This document specifies the requirements for extending the DeepAnalyze API to support Azure Blob Storage and PostgreSQL as data sources. This enhancement will allow users to directly connect to cloud storage and databases without manually uploading files, enabling seamless integration with existing data infrastructure.

## Glossary

- **DeepAnalyze API**: The FastAPI-based server that provides OpenAI-compatible endpoints for data analysis
- **Data Source**: An external system that provides data (Azure Blob Storage, PostgreSQL, local files)
- **Connection**: A configured and authenticated link to a data source
- **Workspace**: An isolated directory where code execution and file operations occur
- **Thread**: A conversation session with its own workspace
- **vLLM**: The model serving backend that runs the DeepAnalyze-8B model
- **Azure Blob Storage**: Microsoft's cloud object storage service
- **PostgreSQL**: An open-source relational database management system
- **Connection String**: A formatted string containing authentication and connection parameters
- **SAS Token**: Shared Access Signature token for Azure Blob Storage authentication
- **SQL Query**: A structured query language statement to retrieve data from PostgreSQL

---

## Requirements

### Requirement 1: Azure Blob Storage Integration

**User Story:** As a data analyst, I want to connect to Azure Blob Storage containers, so that I can analyze files stored in the cloud without manually downloading them.

#### Acceptance Criteria

1. WHEN a user provides Azure Blob Storage connection details THEN the system SHALL authenticate and establish a connection to the specified container
2. WHEN a user lists files in an Azure Blob container THEN the system SHALL return a list of blob names with metadata including size and last modified date
3. WHEN a user requests a file from Azure Blob Storage THEN the system SHALL download the blob to the thread workspace and make it available for analysis
4. WHEN a user uploads analysis results THEN the system SHALL support uploading generated files back to Azure Blob Storage
5. WHEN authentication fails THEN the system SHALL return a clear error message indicating the authentication issue
6. WHEN a blob download fails THEN the system SHALL return an error message with the blob name and failure reason
7. WHEN the system downloads blobs THEN the system SHALL preserve the original file names and extensions

### Requirement 2: PostgreSQL Database Integration

**User Story:** As a data analyst, I want to connect to PostgreSQL databases and query tables, so that I can analyze database data without exporting to CSV files.

#### Acceptance Criteria

1. WHEN a user provides PostgreSQL connection details THEN the system SHALL establish a secure connection to the database
2. WHEN a user lists available tables THEN the system SHALL return table names with schema information
3. WHEN a user executes a SQL query THEN the system SHALL return the results as a pandas DataFrame in the workspace
4. WHEN a user requests table schema information THEN the system SHALL return column names, data types, and constraints
5. WHEN a SQL query fails THEN the system SHALL return a detailed error message including the SQL error code and description
6. WHEN the system executes queries THEN the system SHALL enforce a configurable timeout to prevent long-running queries
7. WHEN the system connects to PostgreSQL THEN the system SHALL use connection pooling for efficient resource management
8. WHEN a user provides read-only credentials THEN the system SHALL prevent any write operations (INSERT, UPDATE, DELETE, DROP)

### Requirement 3: Data Source Management API

**User Story:** As a developer, I want to manage data source connections through API endpoints, so that I can configure and reuse connections across multiple analysis sessions.

#### Acceptance Criteria

1. WHEN a user creates a data source connection THEN the system SHALL store the connection configuration securely
2. WHEN a user lists data sources THEN the system SHALL return all configured connections with metadata but without sensitive credentials
3. WHEN a user deletes a data source THEN the system SHALL remove the connection configuration and invalidate any active connections
4. WHEN a user tests a data source connection THEN the system SHALL verify connectivity and return success or failure status
5. WHEN the system stores credentials THEN the system SHALL encrypt sensitive information at rest
6. WHEN a user retrieves a data source THEN the system SHALL return connection metadata without exposing passwords or tokens

### Requirement 4: Chat API Integration

**User Story:** As a user, I want to reference data sources in chat requests, so that DeepAnalyze can automatically fetch and analyze data from configured sources.

#### Acceptance Criteria

1. WHEN a user sends a chat request with data source references THEN the system SHALL fetch data from the specified sources before analysis
2. WHEN a user specifies Azure Blob paths THEN the system SHALL download the blobs to the thread workspace
3. WHEN a user specifies PostgreSQL queries THEN the system SHALL execute the queries and save results as CSV files in the workspace
4. WHEN data fetching fails THEN the system SHALL return an error message before attempting analysis
5. WHEN multiple data sources are specified THEN the system SHALL fetch all data sources in parallel where possible
6. WHEN the system fetches data THEN the system SHALL include data source information in the prompt template sent to the model

### Requirement 5: Code Execution Environment Enhancement

**User Story:** As a data analyst, I want the code execution environment to have pre-configured database and cloud storage clients, so that generated code can directly interact with data sources.

#### Acceptance Criteria

1. WHEN code is executed in a workspace THEN the system SHALL provide pre-configured Azure Blob Storage clients for authorized containers
2. WHEN code is executed in a workspace THEN the system SHALL provide pre-configured PostgreSQL connection objects for authorized databases
3. WHEN generated code uses data source clients THEN the system SHALL enforce the same authentication and authorization as the API
4. WHEN code attempts unauthorized access THEN the system SHALL raise an exception and return an error message
5. WHEN the system provides database connections THEN the system SHALL automatically close connections after code execution completes

### Requirement 6: Configuration and Security

**User Story:** As a system administrator, I want to configure data source settings and security policies, so that I can control access and protect sensitive credentials.

#### Acceptance Criteria

1. WHEN the system starts THEN the system SHALL load data source configurations from environment variables or configuration files
2. WHEN credentials are stored THEN the system SHALL use encryption with a configurable encryption key
3. WHEN the system accesses credentials THEN the system SHALL decrypt them only in memory and never log them
4. WHEN a user configures a data source THEN the system SHALL validate the connection parameters before storing
5. WHEN the system enforces security policies THEN the system SHALL support IP whitelisting for database connections
6. WHEN the system manages connections THEN the system SHALL implement connection timeout and retry policies

### Requirement 7: Error Handling and Logging

**User Story:** As a developer, I want comprehensive error handling and logging for data source operations, so that I can troubleshoot issues effectively.

#### Acceptance Criteria

1. WHEN a data source operation fails THEN the system SHALL log the error with context including data source ID and operation type
2. WHEN authentication fails THEN the system SHALL log the failure without exposing credentials
3. WHEN a network error occurs THEN the system SHALL retry the operation with exponential backoff up to a configurable maximum
4. WHEN the system encounters errors THEN the system SHALL return user-friendly error messages to the client
5. WHEN the system logs operations THEN the system SHALL include timestamps, request IDs, and user identifiers for audit trails

### Requirement 8: Data Source Discovery and Metadata

**User Story:** As a user, I want to discover available data in connected sources, so that I can understand what data is available for analysis.

#### Acceptance Criteria

1. WHEN a user requests Azure Blob container contents THEN the system SHALL return a hierarchical listing with folder structure
2. WHEN a user requests PostgreSQL database schema THEN the system SHALL return tables, views, and their relationships
3. WHEN a user requests table preview THEN the system SHALL return the first N rows of the table (configurable, default 10)
4. WHEN a user requests column statistics THEN the system SHALL return basic statistics for numeric columns (min, max, mean, count)
5. WHEN the system provides metadata THEN the system SHALL cache metadata for a configurable duration to improve performance

### Requirement 9: Data Source Templates and Examples

**User Story:** As a user, I want example configurations and templates for common data sources, so that I can quickly set up connections.

#### Acceptance Criteria

1. WHEN a user requests data source templates THEN the system SHALL provide example configurations for Azure Blob Storage and PostgreSQL
2. WHEN a user views templates THEN the system SHALL include documentation explaining each configuration parameter
3. WHEN a user creates a connection from a template THEN the system SHALL validate and guide the user through required parameters
4. WHEN the system provides examples THEN the system SHALL include sample SQL queries and blob path patterns

### Requirement 10: Performance and Resource Management

**User Story:** As a system administrator, I want to control resource usage for data source operations, so that the system remains responsive under load.

#### Acceptance Criteria

1. WHEN the system downloads blobs THEN the system SHALL enforce a maximum file size limit (configurable, default 100MB)
2. WHEN the system executes SQL queries THEN the system SHALL enforce a maximum result set size (configurable, default 10,000 rows)
3. WHEN multiple requests access data sources THEN the system SHALL use connection pooling to limit concurrent connections
4. WHEN the system downloads large files THEN the system SHALL stream data to disk rather than loading entirely into memory
5. WHEN the system manages resources THEN the system SHALL clean up temporary files and close connections after thread expiration
