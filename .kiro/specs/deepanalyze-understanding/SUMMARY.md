# DeepAnalyze - Quick Summary

## What is DeepAnalyze?

An **agentic AI system** that autonomously performs data science tasks by:
1. Generating Python code
2. Executing it in a workspace
3. Observing results
4. Iterating until task completion

## Core Architecture (3 Servers)

```
┌─────────────────────────────────────────────────────────┐
│  vLLM Server (Port 8000)                                │
│  - Runs DeepAnalyze-8B model                            │
│  - Generates code and analysis                          │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  API Server (Port 8200)                                 │
│  - FastAPI application                                  │
│  - File management (/v1/files)                          │
│  - Chat completions (/v1/chat/completions)              │
│  - Code execution orchestration                         │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  HTTP File Server (Port 8100)                           │
│  - Serves generated files (charts, reports, etc.)       │
└─────────────────────────────────────────────────────────┘
```

## How It Works (5 Steps)

### 1. User Uploads Data
```bash
POST /v1/files
→ Stores in workspace/_files/
→ Returns file_id
```

### 2. User Sends Analysis Request
```json
{
  "messages": [{
    "role": "user",
    "content": "Analyze this data",
    "file_ids": ["file-abc123"]
  }]
}
```

### 3. System Creates Workspace
```
workspace/thread-xyz/
├── data.csv          (copied from upload)
└── generated/        (for outputs)
```

### 4. Multi-Round Execution Loop
```
Round 1:
  Model: <Code>import pandas as pd; df = pd.read_csv('data.csv')</Code>
  System: Executes code
  System: <Execute>[output]</Execute>
  
Round 2:
  Model: (sees previous output)
  Model: <Code>df.describe()</Code>
  System: Executes code
  System: <Execute>[statistics]</Execute>
  
Round 3:
  Model: <Code>plt.plot(...); plt.savefig('chart.png')</Code>
  System: Executes code
  System: Detects new file: chart.png
  
Round 4:
  Model: <Answer>Analysis complete. See chart.png</Answer>
  System: Stops (Answer tag found)
```

### 5. Return Results
```json
{
  "choices": [{
    "message": {
      "content": "...",
      "files": [
        {"name": "chart.png", "url": "http://localhost:8100/..."}
      ]
    }
  }]
}
```

## Key Components

### 1. DeepAnalyzeVLLM (`deepanalyze.py`)
**The brain** - Orchestrates generation and execution

```python
class DeepAnalyzeVLLM:
    def generate(prompt, workspace):
        for round in range(30):
            response = call_vllm(messages)
            if has_code(response):
                code = extract_code(response)
                output = execute_code(code)
                messages.append(output)
            else:
                break
```

### 2. Chat API (`API/chat_api.py`)
**The orchestrator** - Manages conversations

- Creates thread workspace
- Copies files
- Calls vLLM in loop
- Executes code
- Tracks generated files
- Returns results

### 3. Storage (`API/storage.py`)
**The memory** - Manages state

- Files (uploaded)
- Threads (conversations)
- Messages (history)

### 4. Utils (`API/utils.py`)
**The toolbox** - Helper functions

- `execute_code_safe()` - Run code in subprocess
- `WorkspaceTracker` - Detect new files
- `prepare_vllm_messages()` - Format prompts
- `generate_report_from_messages()` - Create reports

## Code Execution Deep Dive

### Basic Execution (deepanalyze.py)
```python
def execute_code(code_str):
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exec(code_str, {})
    return stdout.getvalue()
```

**Pros:** Simple, fast
**Cons:** No isolation, no timeout

### Advanced Execution (API/utils.py)
```python
def execute_code_safe(code_str, workspace, timeout=120):
    # Write code to temp file
    with open(tmp_file, 'w') as f:
        f.write(code_str)
    
    # Execute in subprocess
    result = subprocess.run(
        [python, tmp_file],
        cwd=workspace,
        timeout=timeout,
        capture_output=True
    )
    
    return result.stdout + result.stderr
```

**Pros:** Process isolation, timeout, environment control
**Cons:** Slower, more complex

## Special Tags

The model uses XML-like tags to structure output:

- `<Analyze>` - Initial analysis
- `<Understand>` - Problem understanding
- `<Code>` - Python code to execute
- `<Execute>` - Execution results (system-injected)
- `<Answer>` - Final answer (stops loop)
- `<File>` - File references

## Workspace Management

### File Tracking
```python
tracker = WorkspaceTracker(workspace, generated_dir)

# Before execution
before = {"data.csv": (1024, timestamp)}

# Execute code that creates chart.png

# After execution
after = {
    "data.csv": (1024, timestamp),
    "chart.png": (4096, new_timestamp)  # NEW!
}

artifacts = tracker.diff_and_collect()
# Returns: [Path("generated/chart.png")]
```

### Automatic Cleanup
- Threads expire after 12 hours
- Workspaces deleted on expiration
- Temporary files cleaned up

## Your Extension: Data Sources

### Goal
Add support for:
1. **Azure Blob Storage** - Cloud file storage
2. **PostgreSQL** - Database queries

### New Workflow
```
User: "Analyze data from Azure container 'sales' and PostgreSQL table 'customers'"
  ↓
System: Fetch from Azure → workspace/sales_data.csv
System: Query PostgreSQL → workspace/customers.csv
  ↓
Model: Sees files in workspace
Model: Generates analysis code
  ↓
System: Executes code
  ↓
Model: Creates visualizations and report
```

### New API Endpoints

```
POST /v1/data-sources
  - Create connection (Azure/PostgreSQL)
  
GET /v1/data-sources
  - List connections
  
GET /v1/data-sources/{id}/browse
  - Browse available data
  
POST /v1/chat/completions
  - Extended with data_source_refs parameter
```

### Implementation Strategy

**1. Create Abstraction Layer**
```python
class DataSourceConnector(ABC):
    def connect(config): pass
    def list_items(): pass
    def fetch_data(identifier, workspace): pass
```

**2. Implement Connectors**
```python
class AzureBlobConnector(DataSourceConnector):
    def fetch_data(blob_path, workspace):
        blob_client.download_blob(blob_path)
        save_to(workspace)

class PostgreSQLConnector(DataSourceConnector):
    def fetch_data(query, workspace):
        df = pd.read_sql(query, connection)
        df.to_csv(workspace / 'query_result.csv')
```

**3. Integrate with Chat API**
```python
# In chat_api.py
if data_source_refs:
    for ref in data_source_refs:
        connector = get_connector(ref.type)
        connector.fetch_data(ref.path, workspace)
```

**4. Update Code Environment**
```python
# Pre-configure clients for generated code
code_setup = """
from azure.storage.blob import BlobServiceClient
import psycopg2

blob_client = BlobServiceClient(...)
db_conn = psycopg2.connect(...)
"""

execute_code_safe(code_setup + user_code, workspace)
```

## Security Considerations

### Current State
- ❌ No authentication
- ❌ No code sandboxing
- ❌ Full file system access
- ✅ Timeout protection
- ✅ Process isolation (API server)

### For Data Sources Extension
- ✅ Encrypt credentials at rest
- ✅ Never log credentials
- ✅ Validate connection parameters
- ✅ Enforce read-only access
- ✅ Implement connection pooling
- ✅ Add audit logging
- ✅ Set resource limits

## Performance Tips

### Current Bottlenecks
1. Model generation (2-3s per round)
2. Code execution (0.5-5s per round)
3. Sequential processing

### Optimization Strategies
1. **Reduce rounds** - Better prompting
2. **Parallel execution** - Multiple workers
3. **Caching** - Cache data fetches
4. **Connection pooling** - Reuse connections
5. **Streaming** - Stream large files

## File Structure

```
DeepAnalyze/
├── deepanalyze.py              # Core inference engine
├── API/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Configuration
│   ├── chat_api.py             # Chat endpoint
│   ├── file_api.py             # File management
│   ├── models_api.py           # Model listing
│   ├── storage.py              # In-memory storage
│   └── utils.py                # Utilities
├── demo/
│   ├── chat/                   # WebUI
│   ├── cli/                    # CLI interface
│   └── jupyter/                # Jupyter integration
├── workspace/
│   ├── _files/                 # Uploaded files
│   └── thread-xxx/             # Thread workspaces
└── .kiro/specs/
    ├── deepanalyze-understanding/
    │   ├── project-analysis.md
    │   ├── detailed-code-execution.md
    │   └── README.md
    └── data-sources-extension/
        └── requirements.md
```

## Quick Commands

### Start vLLM
```bash
vllm serve DeepAnalyze-8B --host 0.0.0.0 --port 8000
```

### Start API Server
```bash
cd API
python start_server.py
```

### Test API
```bash
# Upload file
curl -X POST http://localhost:8200/v1/files \
  -F "file=@data.csv"

# Chat request
curl -X POST http://localhost:8200/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "DeepAnalyze-8B",
    "messages": [{
      "role": "user",
      "content": "Analyze this data",
      "file_ids": ["file-abc123"]
    }]
  }'
```

## Next Steps

1. ✅ **Understand** - Read documentation
2. ✅ **Requirements** - Define what to build
3. ⏭️ **Design** - Plan the implementation
4. ⏭️ **Implement** - Build the features
5. ⏭️ **Test** - Verify it works
6. ⏭️ **Deploy** - Roll it out

## Key Takeaways

1. **Iterative Execution** - The model can try, fail, and retry
2. **Workspace Isolation** - Each conversation is independent
3. **Structured Output** - Tags enable parsing and automation
4. **File Tracking** - Automatic detection of generated files
5. **Extensible Design** - Easy to add new data sources

## Resources

- **Project Analysis**: `.kiro/specs/deepanalyze-understanding/project-analysis.md`
- **Code Execution Details**: `.kiro/specs/deepanalyze-understanding/detailed-code-execution.md`
- **Requirements**: `.kiro/specs/data-sources-extension/requirements.md`
- **API Docs**: `API/README.md`
- **Main README**: `README.md`
