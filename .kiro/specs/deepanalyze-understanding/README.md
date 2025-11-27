# DeepAnalyze Understanding and Extension Specs

## Overview

This directory contains comprehensive documentation for understanding and extending the DeepAnalyze project.

## Documents

### 1. Project Analysis (`project-analysis.md`)
**Comprehensive overview of the entire DeepAnalyze system**

Topics covered:
- Architecture overview with component diagrams
- Core components (DeepAnalyzeVLLM, API Server, Storage)
- API endpoints and their workflows
- Data flow through the system
- Training pipeline and evaluation
- Demo interfaces (WebUI, CLI, JupyterUI)
- Extension points for customization
- Security considerations
- Performance characteristics
- Troubleshooting guide

**Use this document to:**
- Understand the overall system architecture
- Learn how components interact
- Identify where to make changes
- Plan new features

---

### 2. Detailed Code Execution (`detailed-code-execution.md`)
**In-depth analysis of the code generation and execution pipeline**

Topics covered:
- Complete walkthrough of `generate()` method
- Step-by-step execution flow (8 phases)
- Multi-round reasoning loop explained
- Code extraction and parsing
- `execute_code()` implementation details
- Advanced execution with subprocess isolation
- Workspace management and file tracking
- Complete multi-round example with 4 rounds
- Security considerations and mitigations
- Performance characteristics
- Debugging tips

**Use this document to:**
- Understand how code execution works
- Learn about the multi-round reasoning process
- Implement custom execution environments
- Debug execution issues
- Improve security and performance

---

## Extension Spec: Data Sources

### Location: `.kiro/specs/data-sources-extension/`

### Requirements Document (`data-sources-extension/requirements.md`)
**Specification for adding Azure Blob Storage and PostgreSQL support**

Includes 10 comprehensive requirements:

1. **Azure Blob Storage Integration**
   - Authentication and connection
   - File listing and metadata
   - Download and upload operations
   - Error handling

2. **PostgreSQL Database Integration**
   - Database connection management
   - Table listing and schema inspection
   - SQL query execution
   - Read-only enforcement

3. **Data Source Management API**
   - CRUD operations for connections
   - Secure credential storage
   - Connection testing

4. **Chat API Integration**
   - Data source references in requests
   - Automatic data fetching
   - Parallel data source access

5. **Code Execution Environment Enhancement**
   - Pre-configured clients
   - Authorization enforcement
   - Connection lifecycle management

6. **Configuration and Security**
   - Credential encryption
   - Security policies
   - Connection validation

7. **Error Handling and Logging**
   - Comprehensive error messages
   - Audit trails
   - Retry policies

8. **Data Source Discovery and Metadata**
   - Schema inspection
   - Data preview
   - Metadata caching

9. **Data Source Templates and Examples**
   - Example configurations
   - Documentation
   - Sample queries

10. **Performance and Resource Management**
    - Size limits
    - Connection pooling
    - Resource cleanup

---

## Quick Reference

### Key Files in DeepAnalyze

```
deepanalyze.py              # Core inference engine
API/
├── main.py                 # FastAPI application entry
├── config.py               # Configuration constants
├── chat_api.py             # Chat completions endpoint
├── file_api.py             # File management endpoints
├── models_api.py           # Model listing endpoints
├── storage.py              # In-memory storage layer
└── utils.py                # Utility functions
```

### Key Concepts

**Multi-Round Reasoning:**
```
User Request → Generate Code → Execute → Observe Results → 
Generate More Code → Execute → ... → Final Answer
```

**Workspace Isolation:**
```
workspace/
├── _files/                 # Uploaded files
└── thread-xxx/             # Per-conversation workspace
    ├── data.csv            # Copied data files
    └── generated/          # Generated artifacts
        ├── chart.png
        └── report.md
```

**Code Execution Flow:**
```
1. Model generates <Code>...</Code> block
2. System extracts Python code
3. Code executed in subprocess with timeout
4. Output captured (stdout + stderr)
5. Results fed back as <Execute>...</Execute>
6. Model sees results and continues
```

---

## Implementation Roadmap

### Phase 1: Understanding (✅ Complete)
- [x] Analyze project structure
- [x] Document architecture
- [x] Understand code execution
- [x] Identify extension points

### Phase 2: Requirements (✅ Complete)
- [x] Define Azure Blob Storage requirements
- [x] Define PostgreSQL requirements
- [x] Specify API endpoints
- [x] Document security requirements

### Phase 3: Design (Next)
- [ ] Design data source abstraction layer
- [ ] Design API endpoints
- [ ] Design credential management
- [ ] Design code execution integration
- [ ] Create sequence diagrams
- [ ] Define data models

### Phase 4: Implementation
- [ ] Implement data source base classes
- [ ] Implement Azure Blob Storage connector
- [ ] Implement PostgreSQL connector
- [ ] Implement API endpoints
- [ ] Implement credential encryption
- [ ] Update chat API integration
- [ ] Add code execution environment setup

### Phase 5: Testing
- [ ] Unit tests for connectors
- [ ] Integration tests for API
- [ ] Security testing
- [ ] Performance testing
- [ ] End-to-end testing

### Phase 6: Documentation
- [ ] API documentation
- [ ] Configuration guide
- [ ] Security best practices
- [ ] Example usage
- [ ] Troubleshooting guide

---

## Key Insights

### 1. Autonomous Iteration
DeepAnalyze's power comes from its ability to iterate:
- Generate code
- Execute and observe
- Refine approach
- Repeat until success

This is fundamentally different from single-shot code generation.

### 2. Workspace Isolation
Each conversation gets its own workspace:
- Prevents file conflicts
- Enables parallel processing
- Simplifies cleanup
- Improves security

### 3. Structured Output
The model uses XML-like tags to structure its output:
- `<Analyze>` - Analysis
- `<Understand>` - Understanding
- `<Code>` - Executable code
- `<Execute>` - Results (system-injected)
- `<Answer>` - Final answer

This structure enables:
- Parsing and extraction
- Report generation
- Progress tracking
- Error handling

### 4. Subprocess Execution
Using subprocess instead of exec() provides:
- Process isolation
- Timeout enforcement
- Environment control
- Better security

### 5. File Tracking
The WorkspaceTracker automatically detects:
- New files created
- Existing files modified
- Artifacts to return to user

This enables seamless file generation without explicit tracking.

---

## Extension Strategy

### Adding New Data Sources

**Step 1: Create Connector Class**
```python
class DataSourceConnector(ABC):
    @abstractmethod
    def connect(self, config: Dict) -> None:
        pass
    
    @abstractmethod
    def list_items(self) -> List[Dict]:
        pass
    
    @abstractmethod
    def fetch_data(self, identifier: str, workspace: str) -> str:
        pass
```

**Step 2: Implement Specific Connector**
```python
class AzureBlobConnector(DataSourceConnector):
    def connect(self, config: Dict) -> None:
        # Azure-specific connection logic
        pass
```

**Step 3: Register in API**
```python
# In config.py
SUPPORTED_DATA_SOURCES = ["azure_blob", "postgresql", "local"]

# In storage.py
def create_data_source(self, type: str, config: Dict):
    # Store and validate
    pass
```

**Step 4: Integrate with Chat API**
```python
# In chat_api.py
if data_source_refs:
    for ref in data_source_refs:
        connector = get_connector(ref.type)
        connector.fetch_data(ref.path, workspace_dir)
```

**Step 5: Update Code Execution Environment**
```python
# In utils.py execute_code_safe()
# Inject pre-configured clients
code_with_setup = f"""
import azure_client
blob_client = azure_client.get_client('{container}')

{code_str}
"""
```

---

## Security Checklist

When implementing data source extensions:

- [ ] Encrypt credentials at rest
- [ ] Never log credentials
- [ ] Validate all connection parameters
- [ ] Implement connection timeouts
- [ ] Use connection pooling
- [ ] Enforce read-only access where appropriate
- [ ] Implement IP whitelisting
- [ ] Add rate limiting
- [ ] Audit all data access
- [ ] Implement proper error handling
- [ ] Use secure defaults
- [ ] Document security requirements

---

## Performance Checklist

When implementing data source extensions:

- [ ] Implement connection pooling
- [ ] Cache metadata where appropriate
- [ ] Stream large files instead of loading into memory
- [ ] Implement parallel data fetching
- [ ] Set reasonable size limits
- [ ] Add timeout enforcement
- [ ] Monitor resource usage
- [ ] Implement cleanup procedures
- [ ] Use async operations where possible
- [ ] Profile and optimize hot paths

---

## Testing Strategy

### Unit Tests
- Test each connector independently
- Mock external services
- Test error conditions
- Test edge cases

### Integration Tests
- Test API endpoints end-to-end
- Test with real Azure/PostgreSQL instances
- Test concurrent access
- Test resource cleanup

### Security Tests
- Test authentication failures
- Test authorization enforcement
- Test credential encryption
- Test SQL injection prevention

### Performance Tests
- Test with large files
- Test with large result sets
- Test concurrent connections
- Test resource limits

---

## Next Steps

1. **Review Requirements** - Ensure all requirements are clear and complete
2. **Create Design Document** - Design the implementation architecture
3. **Implement Connectors** - Build Azure Blob and PostgreSQL connectors
4. **Update API** - Add new endpoints for data source management
5. **Integrate with Chat** - Enable data source references in chat requests
6. **Test Thoroughly** - Comprehensive testing across all scenarios
7. **Document** - Create user-facing documentation and examples

---

## Questions to Consider

Before implementation, consider:

1. **Authentication**: How will users provide credentials? Environment variables? API parameters? Secure vault?

2. **Authorization**: How will we control which users can access which data sources?

3. **Multi-tenancy**: Will multiple users share data sources or have isolated connections?

4. **Caching**: Should we cache downloaded data? For how long?

5. **Quotas**: Should we limit data source usage per user/thread?

6. **Monitoring**: What metrics should we track for data source operations?

7. **Backwards Compatibility**: How will this affect existing file-based workflows?

8. **Migration**: How will existing users adopt the new data source features?

---

## Resources

### Azure Blob Storage
- [Azure SDK for Python](https://github.com/Azure/azure-sdk-for-python)
- [Blob Storage Documentation](https://docs.microsoft.com/en-us/azure/storage/blobs/)
- [Authentication Methods](https://docs.microsoft.com/en-us/azure/storage/common/storage-auth)

### PostgreSQL
- [psycopg2 Documentation](https://www.psycopg.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Best Practices](https://wiki.postgresql.org/wiki/Don%27t_Do_This)

### Security
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Cryptography](https://cryptography.io/en/latest/)
- [Secrets Management](https://12factor.net/config)

---

## Contact

For questions or clarifications about this documentation:
- Review the source code in the DeepAnalyze repository
- Check the API README at `API/README.md`
- Refer to the main project README at `README.md`
