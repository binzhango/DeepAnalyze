# DeepAnalyze Project - Comprehensive Analysis

## Executive Summary

**DeepAnalyze** is an agentic Large Language Model (LLM) system designed for autonomous data science tasks. It's built on top of DeepSeek-R1-0528-Qwen3-8B and can autonomously complete data analysis, modeling, visualization, and report generation without human intervention.

**Key Capabilities:**
- Autonomous execution of entire data science pipelines
- Support for structured (CSV, Excel, Databases), semi-structured (JSON, XML), and unstructured data (TXT, Markdown)
- Code generation and execution with iterative refinement
- Multi-round reasoning with code execution feedback loops
- OpenAI-compatible API for easy integration

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                       │
│  (WebUI / CLI / JupyterUI / API Clients)                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              DeepAnalyze API Server (Port 8200)             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI Application                                  │  │
│  │  - File Management API (/v1/files)                   │  │
│  │  - Chat Completions API (/v1/chat/completions)       │  │
│  │  - Models API (/v1/models)                           │  │
│  │  - Admin API (/v1/admin)                             │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              vLLM Model Server (Port 8000)                  │
│              DeepAnalyze-8B Model                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│           HTTP File Server (Port 8100)                      │
│           Serves generated files and artifacts              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Workspace File System                          │
│  workspace/                                                 │
│  ├── _files/          (uploaded files storage)             │
│  ├── thread-xxx/      (per-conversation workspace)         │
│  │   ├── data files   (copied from uploads)                │
│  │   └── generated/   (generated artifacts)                │
│  └── thread-yyy/                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. DeepAnalyzeVLLM Class (`deepanalyze.py`)

**Purpose:** Core inference engine that orchestrates multi-round reasoning and code execution.

**Key Methods:**
- `__init__(model_name, api_url, max_rounds)` - Initialize with vLLM endpoint
- `generate(prompt, workspace, temperature, max_tokens)` - Main generation loop
- `execute_code(code_str)` - Execute Python code and capture output

**Workflow:**
1. Send prompt to vLLM API
2. Parse response for `<Code>...</Code>` blocks
3. Extract and execute Python code in workspace
4. Capture execution output
5. Feed output back as `<Execute>...</Execute>` message
6. Repeat until `<Answer>` tag or max rounds reached

**Special Tags:**
- `<Code>` - Contains Python code to execute
- `<Execute>` - Contains execution results (stdout/stderr)
- `<Answer>` - Final answer, terminates the loop
- `<Analyze>` - Analysis section
- `<Understand>` - Understanding section
- `<File>` - File references

---

### 2. API Server (`API/`)

#### 2.1 Main Application (`main.py`)

**Purpose:** FastAPI application entry point with CORS support.

**Features:**
- Health check endpoint (`/health`)
- Router registration for all API modules
- HTTP file server thread management
- Graceful shutdown handling

#### 2.2 Configuration (`config.py`)

**Key Settings:**
```python
API_BASE = "http://localhost:8000/v1"  # vLLM endpoint
MODEL_PATH = "DeepAnalyze-8B"
WORKSPACE_BASE_DIR = "workspace"
HTTP_SERVER_PORT = 8100
API_PORT = 8200
MAX_NEW_TOKENS = 32768
CODE_EXECUTION_TIMEOUT = 120
STOP_TOKEN_IDS = [151676, 151645]  # DeepAnalyze special tokens
```

#### 2.3 File Management API (`file_api.py`)

**Endpoints:**
- `POST /v1/files` - Upload files
- `GET /v1/files` - List all files
- `GET /v1/files/{file_id}` - Get file metadata
- `GET /v1/files/{file_id}/content` - Download file content
- `DELETE /v1/files/{file_id}` - Delete file

**Features:**
- OpenAI-compatible file API
- Persistent file storage in `workspace/_files/`
- File purpose validation (fine-tune, answers, file-extract, assistants)

#### 2.4 Chat Completions API (`chat_api.py`)

**Endpoint:** `POST /v1/chat/completions`

**Key Features:**
- OpenAI-compatible chat API with extensions
- File attachment support via `file_ids` parameter
- Streaming and non-streaming responses
- Automatic code execution workflow
- Generated file tracking and URL generation
- Report generation from conversation history

**Request Format:**
```json
{
  "model": "DeepAnalyze-8B",
  "messages": [
    {
      "role": "user",
      "content": "Analyze this data",
      "file_ids": ["file-abc123"]
    }
  ],
  "temperature": 0.4,
  "stream": false
}
```

**Response Format:**
```json
{
  "id": "chatcmpl-xyz789",
  "object": "chat.completion",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "...",
      "files": [
        {"name": "chart.png", "url": "http://..."}
      ]
    }
  }],
  "generated_files": [...],
  "attached_files": [...]
}
```

**Workflow:**
1. Create temporary thread workspace
2. Copy attached files to workspace
3. Build DeepAnalyze prompt template
4. Enter multi-round generation loop:
   - Call vLLM API
   - Parse for `<Code>` blocks
   - Execute code in workspace
   - Track generated files
   - Feed execution results back
5. Generate conversation report
6. Return response with file URLs

#### 2.5 Models API (`models_api.py`)

**Endpoints:**
- `GET /v1/models` - List available models
- `GET /v1/models/{model_id}` - Get model details

**Purpose:** OpenAI-compatible model listing.

#### 2.6 Storage Layer (`storage.py`)

**Purpose:** In-memory storage for API objects with thread safety.

**Managed Objects:**
- Files: Uploaded file metadata and paths
- Threads: Conversation threads with workspaces
- Messages: Thread message history

**Key Methods:**
- `create_file()`, `get_file()`, `delete_file()`, `list_files()`
- `create_thread()`, `get_thread()`, `delete_thread()`
- `create_message()`, `list_messages()`
- `cleanup_expired_threads()` - Remove old threads (12h timeout)

**Thread Workspace Management:**
- Each thread gets isolated workspace directory
- Files copied to thread workspace on creation
- Automatic cleanup of expired threads

#### 2.7 Utilities (`utils.py`)

**Key Functions:**

**Workspace Management:**
- `get_thread_workspace(thread_id)` - Get workspace path
- `build_download_url(thread_id, rel_path)` - Build file URLs
- `WorkspaceTracker` - Track file changes and collect artifacts

**Message Processing:**
- `prepare_vllm_messages()` - Convert to DeepAnalyze format
- `_normalize_openai_message_content()` - Normalize message content
- `collect_file_info()` - Build file listing for prompt

**Code Execution:**
- `execute_code_safe()` - Sync code execution with timeout
- `execute_code_safe_async()` - Async code execution
- `extract_code_from_segment()` - Parse code from `<Code>` tags

**Report Generation:**
- `extract_sections_from_history()` - Build report from tagged sections
- `save_markdown_report()` - Save markdown report
- `generate_report_from_messages()` - Generate conversation report
- `render_file_block()` - Build file reference blocks

**HTTP Server:**
- `start_http_server()` - Serve workspace files on port 8100

---

## Data Flow

### Complete Request Flow

```
1. Client uploads files
   POST /v1/files
   ↓
   Files stored in workspace/_files/
   Returns file_id

2. Client sends chat request with file_ids
   POST /v1/chat/completions
   ↓
   Create thread workspace (workspace/thread-xxx/)
   Copy files to thread workspace
   ↓
   Build DeepAnalyze prompt:
   # Instruction
   <user message>
   
   # Data
   File 1: {"name": "data.csv", "size": "10KB"}
   ...
   ↓
   Send to vLLM API (port 8000)
   ↓
   Receive response with <Code> block
   ↓
   Extract Python code
   Execute in thread workspace
   Capture output
   ↓
   Track new/modified files → copy to generated/
   ↓
   Feed execution result back:
   <Execute>
   [output]
   </Execute>
   ↓
   Repeat until <Answer> or max_rounds
   ↓
   Generate conversation report
   Save to generated/Conversation_Report_*.md
   ↓
   Build file URLs (http://localhost:8100/thread-xxx/generated/...)
   ↓
   Return response with:
   - Assistant message content
   - Generated files list with URLs
   - Attached files list

3. Client downloads generated files
   GET http://localhost:8100/thread-xxx/generated/chart.png
   ↓
   HTTP server serves from workspace/
```

---

## Prompt Template

DeepAnalyze uses a specific prompt structure:

```
# Instruction
<user's task description>

# Data
File 1:
{"name": "data.csv", "size": "10.6KB"}
File 2:
{"name": "analysis.xlsx", "size": "4.8KB"}
...
```

The model responds with structured tags:
- `<Analyze>` - Initial analysis
- `<Understand>` - Understanding of the problem
- `<Code>` - Python code to execute
- `<Execute>` - Execution results (injected by system)
- `<Answer>` - Final answer

---

## Training Pipeline

Located in `deepanalyze/` directory:

### 1. Base Model Preparation
- Start with DeepSeek-R1-0528-Qwen3-8B
- Add special tokens using `add_vocab.py`

### 2. Training Data
- **DataScience-Instruct-500K** dataset
- Sources: Reasoning-Table, Spider, BIRD, DABStep
- Includes SFT and RL data

### 3. Training Stages
- **Single-ability Fine-tuning** (`scripts/single.sh`)
- **Multi-ability Cold Start** (`scripts/multi_coldstart.sh`)
- **Multi-ability RL** (`scripts/multi_rl.sh`)

### 4. Training Frameworks
- **ms-swift**: Model fine-tuning framework
- **SkyRL**: Reinforcement learning framework

---

## Demo Interfaces

### 1. WebUI (`demo/chat/`)
- Next.js + React application
- Three-panel interface
- Real-time streaming responses
- File upload and download
- Port: 4000

### 2. CLI (`demo/cli/`)
- Rich-based terminal interface
- File upload support
- Streaming responses
- English and Chinese versions

### 3. JupyterUI (`demo/jupyter/`)
- MCP (Model Context Protocol) server
- Integrates with Jupyter Lab
- Converts tags to notebook cells:
  - `<Analyze|Understand|Answer>` → Markdown cells
  - `<Code>` → Code cells (auto-executed)

---

## Evaluation & Benchmarks

Located in `playground/`:

### Supported Benchmarks
- **DS-1000**: Data science coding benchmark
- **DSBench**: Data analysis and modeling
- **TableQA**: Table question answering
- **DABStep-Research**: Research tasks

### Evaluation Scripts
- Unified vLLM-based evaluation
- Distributed inference support
- Result comparison with GPT models

---

## Key Design Patterns

### 1. Multi-Round Reasoning Loop
```python
for round in range(max_rounds):
    response = call_vllm_api(messages)
    if has_code_block(response):
        code = extract_code(response)
        output = execute_code(code)
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "execute", "content": output})
    else:
        break
```

### 2. Workspace Isolation
- Each conversation gets isolated workspace
- Files copied to workspace for safety
- Generated files tracked and collected
- Automatic cleanup of old workspaces

### 3. Code Execution Safety
- Subprocess execution with timeout
- Separate process for isolation
- Environment variable control (MPLBACKEND=Agg)
- Error capture and formatting

### 4. File Tracking
- `WorkspaceTracker` monitors file changes
- Detects new and modified files
- Copies artifacts to `generated/` folder
- Builds download URLs for client access

### 5. Streaming Support
- Server-Sent Events (SSE) format
- Chunk-by-chunk content delivery
- Execution results streamed in real-time
- Final chunk includes generated files

---

## Extension Points

### 1. Custom Data Sources
- Add new file format parsers in `utils.py`
- Extend `collect_file_info()` for metadata extraction
- Support database connections

### 2. Custom Tools
- Add tool definitions in `config.py`
- Implement tool execution in `chat_api.py`
- Extend prompt template with tool descriptions

### 3. Custom Models
- Update `MODEL_PATH` in `config.py`
- Adjust `STOP_TOKEN_IDS` for model-specific tokens
- Modify prompt template if needed

### 4. Custom Execution Environments
- Extend `execute_code_safe()` for other languages
- Add Docker/container execution
- Implement resource limits (memory, CPU)

### 5. Enhanced Storage
- Replace in-memory storage with database
- Add persistent thread history
- Implement user authentication

### 6. Advanced Features
- Multi-agent collaboration
- Long-term memory
- External API integrations
- Custom visualization libraries

---

## Dependencies

### Core Dependencies
- `vllm>=0.8.5` - Model serving
- `torch` - Deep learning framework
- `transformers` - Model loading
- `fastapi` - API server
- `uvicorn` - ASGI server
- `openai` - Client library

### Data Science Libraries
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `scikit-learn` - Machine learning
- `matplotlib` - Plotting
- `seaborn` - Statistical visualization

### Training Dependencies
- `ms-swift` - Fine-tuning framework
- `SkyRL` - RL training framework

---

## Configuration Summary

### Ports
- **8000**: vLLM model server
- **8200**: DeepAnalyze API server
- **8100**: HTTP file server
- **4000**: WebUI (optional)

### Directories
- `workspace/` - Working directory
  - `_files/` - Uploaded files
  - `thread-xxx/` - Thread workspaces
    - `generated/` - Generated artifacts
- `API/` - API server code
- `demo/` - Demo interfaces
- `deepanalyze/` - Training code
- `playground/` - Evaluation benchmarks

### Environment Variables
- `MPLBACKEND=Agg` - Matplotlib backend
- `QT_QPA_PLATFORM=offscreen` - Qt platform

---

## Security Considerations

### Current Implementation
- No authentication/authorization
- Code execution without sandboxing
- File system access unrestricted
- No rate limiting

### Recommendations for Production
1. Add user authentication (JWT, OAuth)
2. Implement code execution sandboxing (Docker, gVisor)
3. Add rate limiting and quotas
4. Restrict file system access
5. Validate and sanitize all inputs
6. Add audit logging
7. Implement resource limits (CPU, memory, disk)
8. Use HTTPS for all connections
9. Add input validation for file uploads
10. Implement CORS properly for production

---

## Performance Characteristics

### Scalability
- Single-threaded code execution (bottleneck)
- In-memory storage (limited by RAM)
- No horizontal scaling support
- File server is single-threaded

### Optimization Opportunities
1. Parallel code execution for multiple requests
2. Database-backed storage
3. Distributed file storage (S3, MinIO)
4. Load balancing for API servers
5. Caching for frequently accessed files
6. Async execution throughout

---

## Common Use Cases

### 1. Data Analysis Report Generation
```python
prompt = "Generate a comprehensive data analysis report"
files = ["sales_data.csv", "customer_data.xlsx"]
```

### 2. Exploratory Data Analysis
```python
prompt = "Perform EDA and identify key patterns"
files = ["dataset.csv"]
```

### 3. Machine Learning Modeling
```python
prompt = "Build and evaluate a predictive model"
files = ["training_data.csv", "test_data.csv"]
```

### 4. Data Visualization
```python
prompt = "Create visualizations showing trends over time"
files = ["time_series.csv"]
```

### 5. Statistical Analysis
```python
prompt = "Conduct statistical tests and report findings"
files = ["experiment_results.csv"]
```

---

## Troubleshooting Guide

### Common Issues

**1. vLLM Connection Failed**
- Check vLLM server is running on port 8000
- Verify `API_BASE` in `config.py`
- Check firewall settings

**2. Code Execution Timeout**
- Increase `CODE_EXECUTION_TIMEOUT` in `config.py`
- Check for infinite loops in generated code
- Monitor system resources

**3. File Not Found**
- Verify file uploaded successfully
- Check `workspace/_files/` directory
- Ensure file_id is correct

**4. Generated Files Not Accessible**
- Check HTTP server is running on port 8100
- Verify file permissions
- Check `workspace/thread-xxx/generated/` directory

**5. Out of Memory**
- Reduce `MAX_NEW_TOKENS`
- Implement thread cleanup
- Monitor workspace disk usage

---

## Next Steps for Customization

Based on your requirements, you can:

1. **Extend the API** - Add custom endpoints for specific workflows
2. **Custom Data Sources** - Integrate databases, APIs, cloud storage
3. **Enhanced Security** - Add authentication and sandboxing
4. **Custom Tools** - Add domain-specific tools and libraries
5. **UI Customization** - Modify WebUI for your branding
6. **Model Fine-tuning** - Train on domain-specific data
7. **Integration** - Connect with existing systems
8. **Monitoring** - Add logging, metrics, and alerting

---

## Summary

DeepAnalyze is a well-architected agentic system that combines:
- **LLM reasoning** (via vLLM)
- **Code execution** (Python subprocess)
- **File management** (workspace isolation)
- **API compatibility** (OpenAI-style)
- **Multi-round iteration** (feedback loops)

The modular design makes it easy to extend and customize for specific use cases while maintaining the core autonomous data science capabilities.
