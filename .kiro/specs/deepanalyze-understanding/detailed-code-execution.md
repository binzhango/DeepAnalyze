# DeepAnalyze Code Execution - Detailed Analysis

## Overview

DeepAnalyze's core capability is its ability to generate Python code, execute it, observe the results, and iteratively refine its approach. This document provides an in-depth analysis of the `generate()` and `execute_code()` methods.

---

## The `generate()` Method

### Location
`deepanalyze.py` - `DeepAnalyzeVLLM.generate()`

### Method Signature
```python
def generate(
    self,
    prompt: str,           # User's instruction/question
    workspace: str,        # Working directory for code execution
    temperature: float = 0.5,  # Sampling temperature
    max_tokens: int = 32768,   # Maximum tokens to generate
    top_p: float = None,       # Nucleus sampling parameter
    top_k: int = None,         # Top-k sampling parameter
) -> dict:
```

### Return Value
```python
{
    "reasoning": str  # Complete conversation including all rounds
}
```

---

## Step-by-Step Execution Flow

### Phase 1: Initialization

```python
original_cwd = os.getcwd()
os.chdir(workspace)  # Change to workspace directory
reasoning = ""
messages = [{"role": "user", "content": prompt}]
response_message = []
```

**What happens:**
1. Save current working directory
2. Change to the workspace directory (where data files are located)
3. Initialize conversation with user's prompt
4. Prepare to collect all responses

---

### Phase 2: Multi-Round Generation Loop

```python
for round_idx in range(self.max_rounds):  # Default: 30 rounds
```

The system can iterate up to 30 times, allowing the model to:
- Generate code
- Execute it
- Observe results
- Generate more code based on results
- Repeat until task is complete

---

### Phase 3: API Call to vLLM

```python
payload = {
    "model": self.model_name,
    "messages": messages,
    "temperature": temperature,
    "max_tokens": max_tokens,
    "add_generation_prompt": False,
    "stop": ["</Code>"],  # Stop when code block closes
}

response = requests.post(
    self.api_url,  # http://localhost:8000/v1/chat/completions
    headers={"Content-Type": "application/json"},
    json=payload,
)
```

**Key Points:**
- `stop: ["</Code>"]` - Stops generation when `</Code>` tag is encountered
- This allows streaming execution: generate code → execute → continue
- `add_generation_prompt: False` - Model handles its own prompt formatting

---

### Phase 4: Response Processing

```python
ans = response_data["choices"][0]["message"]["content"]

# Handle stop reason
if response_data["choices"][0].get("stop_reason") == "</Code>":
    ans += "</Code>"  # Add closing tag if stopped early

response_message.append(ans)
```

**Example Response:**
```
<Analyze>
I need to load the CSV file and examine its structure.
</Analyze>

<Code>
```python
import pandas as pd

df = pd.read_csv('data.csv')
print(df.head())
print(df.info())
```
</Code>
```

---

### Phase 5: Code Detection and Extraction

```python
# Check for <Code> block
code_match = re.search(r"<Code>(.*?)</Code>", ans, re.DOTALL)

if not code_match or "<Answer>" in ans:
    break  # No code to execute or final answer reached
```

**Two exit conditions:**
1. No `<Code>` block found → Model is done
2. `<Answer>` tag found → Final answer provided

**Code Extraction:**
```python
code_content = code_match.group(1).strip()

# Handle markdown code fences
md_match = re.search(r"```(?:python)?(.*?)```", code_content, re.DOTALL)
code_str = md_match.group(1).strip() if md_match else code_content
```

**Supports both formats:**
```
<Code>
import pandas as pd
df = pd.read_csv('data.csv')
</Code>
```

```
<Code>
```python
import pandas as pd
df = pd.read_csv('data.csv')
```
</Code>
```

---

### Phase 6: Code Execution

```python
exe_output = self.execute_code(code_str)
response_message.append(f"<Execute>\n{exe_output}\n</Execute>")
```

**Example Execution Output:**
```
<Execute>
   col1  col2  col3
0     1     2     3
1     4     5     6

<class 'pandas.core.frame.DataFrame'>
RangeIndex: 2 entries, 0 to 1
Data columns (total 3 columns):
 #   Column  Non-Null Count  Dtype
---  ------  --------------  -----
 0   col1    2 non-null      int64
 1   col2    2 non-null      int64
 2   col3    2 non-null      int64
dtypes: int64(3)
memory usage: 176.0 bytes
</Execute>
```

---

### Phase 7: Feedback Loop

```python
# Append messages for next round
messages.append({"role": "assistant", "content": ans})
messages.append({"role": "execute", "content": exe_output})
```

**Conversation History:**
```python
[
    {"role": "user", "content": "Analyze data.csv"},
    {"role": "assistant", "content": "<Analyze>...</Analyze>\n<Code>...</Code>"},
    {"role": "execute", "content": "[execution output]"},
    {"role": "assistant", "content": "<Analyze>...</Analyze>\n<Code>...</Code>"},
    {"role": "execute", "content": "[execution output]"},
    # ... continues until <Answer>
]
```

The model sees:
1. Original user request
2. Its previous analysis and code
3. Execution results
4. Can now generate next step based on results

---

### Phase 8: Completion

```python
reasoning = "\n".join(response_message)
os.chdir(original_cwd)  # Restore original directory
return {"reasoning": reasoning}
```

**Final Output Structure:**
```
<Analyze>
Initial analysis...
</Analyze>

<Code>
```python
# First code block
```
</Code>

<Execute>
[First execution output]
</Execute>

<Understand>
Based on the results, I can see...
</Understand>

<Code>
```python
# Second code block
```
</Code>

<Execute>
[Second execution output]
</Execute>

<Answer>
Final answer and conclusions...
</Answer>
```

---

## The `execute_code()` Method

### Location
`deepanalyze.py` - `DeepAnalyzeVLLM.execute_code()`

### Method Signature
```python
def execute_code(self, code_str: str) -> str:
```

### Execution Strategy

**Uses `exec()` with isolated namespace:**
```python
exec(code_str, {})  # Empty globals dict for isolation
```

---

### Output Capture Mechanism

```python
stdout_capture = io.StringIO()
stderr_capture = io.StringIO()

with contextlib.redirect_stdout(stdout_capture), \
     contextlib.redirect_stderr(stderr_capture):
    exec(code_str, {})

output = stdout_capture.getvalue()
if stderr_capture.getvalue():
    output += stderr_capture.getvalue()
```

**Captures:**
- `print()` statements → stdout
- Warnings → stderr
- Errors → stderr (before exception)

---

### Error Handling

```python
except Exception as exec_error:
    code_lines = code_str.splitlines()
    tb_lines = traceback.format_exc().splitlines()
    error_line = None
    
    # Extract line number from traceback
    for line in tb_lines:
        if 'File "<string>", line' in line:
            line_num = int(line.split(", line ")[1].split(",")[0])
            error_line = line_num
            break
```

**Error Output Format:**
```
[Error]:
Traceback (most recent call last):
  File "<string>", line 5, in <module>
    result = 10 / 0
ZeroDivisionError: division by zero
```

**Includes:**
1. Error type (ZeroDivisionError)
2. Error message (division by zero)
3. Line number where error occurred
4. The actual line of code that failed

---

## Advanced Code Execution (API Server)

### Location
`API/utils.py` - `execute_code_safe()` and `execute_code_safe_async()`

### Key Differences from Basic Execution

#### 1. Subprocess Isolation

```python
def execute_code_safe(code_str: str, workspace_dir: str, timeout_sec: int = 120) -> str:
```

**Uses subprocess instead of exec():**
```python
# Create temporary Python file
fd, tmp_path = tempfile.mkstemp(suffix=".py", dir=exec_cwd)
with open(tmp_path, "w", encoding="utf-8") as f:
    f.write(code_str)

# Execute in separate process
completed = subprocess.run(
    [sys.executable, tmp_path],
    cwd=exec_cwd,
    capture_output=True,
    text=True,
    timeout=timeout_sec,
    env=child_env,
)
```

**Benefits:**
- Process isolation (crashes don't affect server)
- Timeout enforcement (kills runaway code)
- Environment control
- Resource limits (via OS)

---

#### 2. Environment Configuration

```python
child_env = os.environ.copy()
child_env.setdefault("MPLBACKEND", "Agg")  # Matplotlib headless mode
child_env.setdefault("QT_QPA_PLATFORM", "offscreen")  # Qt headless
child_env.pop("DISPLAY", None)  # Remove display variable
```

**Why this matters:**
- `MPLBACKEND=Agg` - Allows matplotlib to work without GUI
- `QT_QPA_PLATFORM=offscreen` - Qt apps work without display
- No `DISPLAY` - Prevents GUI window attempts

**Example - This works in headless environment:**
```python
import matplotlib.pyplot as plt
plt.plot([1, 2, 3], [4, 5, 6])
plt.savefig('chart.png')  # Saves to file instead of showing
```

---

#### 3. Timeout Handling

```python
try:
    completed = subprocess.run(
        [sys.executable, tmp_path],
        timeout=timeout_sec,  # Default: 120 seconds
    )
except subprocess.TimeoutExpired:
    return f"[Timeout]: execution exceeded {timeout_sec} seconds"
```

**Prevents:**
- Infinite loops
- Long-running computations
- Hanging network requests
- Resource exhaustion

---

#### 4. Async Version

```python
async def execute_code_safe_async(
    code_str: str, workspace_dir: str, timeout_sec: int = 120
) -> str:
```

**Uses asyncio subprocess:**
```python
process = await asyncio.create_subprocess_exec(
    sys.executable, tmp_path,
    cwd=exec_cwd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    env=child_env,
)

try:
    stdout, stderr = await asyncio.wait_for(
        process.communicate(),
        timeout=timeout_sec
    )
except asyncio.TimeoutError:
    process.kill()
    await process.wait()
    return f"[Timeout]: execution exceeded {timeout_sec} seconds"
```

**Benefits:**
- Non-blocking execution
- Server can handle other requests
- Better resource utilization
- Proper async/await integration

---

## Workspace Management During Execution

### File Tracking with WorkspaceTracker

```python
tracker = WorkspaceTracker(workspace_dir, generated_dir)
```

**Before code execution:**
```python
before_state = {
    "data.csv": (1024, 1234567890),  # (size, mtime)
    "config.json": (512, 1234567800),
}
```

**After code execution:**
```python
after_state = {
    "data.csv": (1024, 1234567890),  # Unchanged
    "config.json": (512, 1234567800),  # Unchanged
    "chart.png": (4096, 1234567900),  # NEW FILE
    "results.csv": (2048, 1234567905),  # NEW FILE
}
```

**Detected changes:**
```python
artifacts = tracker.diff_and_collect()
# Returns: [Path("generated/chart.png"), Path("generated/results.csv")]
```

**These files are:**
1. Copied to `generated/` folder
2. Made available via HTTP server
3. URLs returned to client

---

## Complete Example: Multi-Round Execution

### User Request
```
"Analyze sales_data.csv and create visualizations"
```

### Round 1: Data Loading

**Model generates:**
```
<Analyze>
I need to first load and examine the data structure.
</Analyze>

<Code>
```python
import pandas as pd

df = pd.read_csv('sales_data.csv')
print("Shape:", df.shape)
print("\nColumns:", df.columns.tolist())
print("\nFirst few rows:")
print(df.head())
print("\nData types:")
print(df.dtypes)
```
</Code>
```

**Execution output:**
```
<Execute>
Shape: (1000, 5)

Columns: ['date', 'product', 'quantity', 'price', 'region']

First few rows:
         date product  quantity  price region
0  2024-01-01   Apple        10   1.50   East
1  2024-01-01  Banana        15   0.80   West
2  2024-01-02   Apple         8   1.50   East
3  2024-01-02  Orange        12   1.20  South
4  2024-01-03  Banana        20   0.80   West

Data types:
date        object
product     object
quantity     int64
price      float64
region      object
dtype: object
</Execute>
```

---

### Round 2: Data Analysis

**Model generates (based on Round 1 results):**
```
<Understand>
The data has 1000 rows with sales information. I can see:
- Date column needs to be converted to datetime
- 5 columns: date, product, quantity, price, region
- Need to calculate total sales (quantity * price)
</Understand>

<Code>
```python
import pandas as pd

df = pd.read_csv('sales_data.csv')
df['date'] = pd.to_datetime(df['date'])
df['total_sales'] = df['quantity'] * df['price']

# Summary statistics
print("Total Sales by Product:")
print(df.groupby('product')['total_sales'].sum().sort_values(ascending=False))

print("\nTotal Sales by Region:")
print(df.groupby('region')['total_sales'].sum().sort_values(ascending=False))

print("\nOverall Statistics:")
print(f"Total Revenue: ${df['total_sales'].sum():.2f}")
print(f"Average Order Value: ${df['total_sales'].mean():.2f}")
```
</Code>
```

**Execution output:**
```
<Execute>
Total Sales by Product:
product
Apple     15000.00
Banana    12000.00
Orange     9600.00
Name: total_sales, dtype: float64

Total Sales by Region:
region
East     14500.00
West     12800.00
South     9300.00
Name: total_sales, dtype: float64

Overall Statistics:
Total Revenue: $36600.00
Average Order Value: $36.60
</Execute>
```

---

### Round 3: Visualization

**Model generates:**
```
<Code>
```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('sales_data.csv')
df['date'] = pd.to_datetime(df['date'])
df['total_sales'] = df['quantity'] * df['price']

# Create visualizations
fig, axes = plt.subplots(2, 2, figsize=(15, 12))

# 1. Sales by Product
product_sales = df.groupby('product')['total_sales'].sum().sort_values(ascending=False)
axes[0, 0].bar(product_sales.index, product_sales.values)
axes[0, 0].set_title('Total Sales by Product')
axes[0, 0].set_ylabel('Sales ($)')

# 2. Sales by Region
region_sales = df.groupby('region')['total_sales'].sum().sort_values(ascending=False)
axes[0, 1].bar(region_sales.index, region_sales.values, color='orange')
axes[0, 1].set_title('Total Sales by Region')
axes[0, 1].set_ylabel('Sales ($)')

# 3. Sales over time
daily_sales = df.groupby('date')['total_sales'].sum()
axes[1, 0].plot(daily_sales.index, daily_sales.values)
axes[1, 0].set_title('Daily Sales Trend')
axes[1, 0].set_xlabel('Date')
axes[1, 0].set_ylabel('Sales ($)')
axes[1, 0].tick_params(axis='x', rotation=45)

# 4. Product distribution
product_counts = df['product'].value_counts()
axes[1, 1].pie(product_counts.values, labels=product_counts.index, autopct='%1.1f%%')
axes[1, 1].set_title('Product Distribution')

plt.tight_layout()
plt.savefig('sales_analysis.png', dpi=300, bbox_inches='tight')
print("Visualization saved as sales_analysis.png")
```
</Code>
```

**Execution output:**
```
<Execute>
Visualization saved as sales_analysis.png
</Execute>
```

**File tracking detects:**
- New file: `sales_analysis.png`
- Copied to: `workspace/thread-xxx/generated/sales_analysis.png`
- URL: `http://localhost:8100/thread-xxx/generated/sales_analysis.png`

---

### Round 4: Final Answer

**Model generates:**
```
<Answer>
# Sales Data Analysis Report

## Summary
I've analyzed the sales_data.csv file containing 1000 sales records across multiple products and regions.

## Key Findings

### Revenue Analysis
- **Total Revenue**: $36,600.00
- **Average Order Value**: $36.60

### Top Performing Products
1. Apple: $15,000.00 (41% of total sales)
2. Banana: $12,000.00 (33% of total sales)
3. Orange: $9,600.00 (26% of total sales)

### Regional Performance
1. East: $14,500.00 (40% of total sales)
2. West: $12,800.00 (35% of total sales)
3. South: $9,300.00 (25% of total sales)

## Visualizations
I've created a comprehensive visualization (sales_analysis.png) showing:
- Bar charts for product and regional sales
- Time series trend of daily sales
- Pie chart showing product distribution

## Recommendations
1. Focus marketing efforts on Apple products (highest revenue)
2. Investigate growth opportunities in South region (lowest sales)
3. Monitor daily sales trends for seasonal patterns
</Answer>
```

**Loop terminates** because `<Answer>` tag is present.

---

## Security Considerations

### Current Limitations

1. **No Sandboxing**
   - Code runs with full Python capabilities
   - Can access file system
   - Can make network requests
   - Can import any library

2. **Resource Limits**
   - Only timeout protection (120 seconds)
   - No memory limits
   - No CPU limits
   - No disk space limits

3. **Dangerous Operations Possible**
   ```python
   # These would all execute:
   import os
   os.system('rm -rf /')  # Dangerous!
   
   import subprocess
   subprocess.run(['curl', 'evil.com'])  # Network access
   
   with open('/etc/passwd', 'r') as f:  # File system access
       print(f.read())
   ```

### Recommended Mitigations

1. **Use Docker/Containers**
   ```python
   docker run --rm \
     --network none \
     --memory 512m \
     --cpus 0.5 \
     --read-only \
     -v workspace:/workspace:ro \
     python:3.12 python /workspace/code.py
   ```

2. **Use RestrictedPython**
   ```python
   from RestrictedPython import compile_restricted
   
   code = compile_restricted(code_str, '<string>', 'exec')
   exec(code, safe_globals)
   ```

3. **Use gVisor/Firecracker**
   - Lightweight VM isolation
   - Better than containers
   - Near-native performance

4. **Whitelist Imports**
   ```python
   ALLOWED_MODULES = {'pandas', 'numpy', 'matplotlib', 'seaborn'}
   
   def safe_import(name, *args, **kwargs):
       if name not in ALLOWED_MODULES:
           raise ImportError(f"Module {name} not allowed")
       return __import__(name, *args, **kwargs)
   ```

---

## Performance Characteristics

### Execution Time Breakdown

**Typical request (3 rounds):**
```
Round 1: Generate (2s) + Execute (0.5s) = 2.5s
Round 2: Generate (3s) + Execute (1s) = 4s
Round 3: Generate (2s) + Execute (5s) = 7s
Total: ~13.5 seconds
```

**Bottlenecks:**
1. Model generation (2-3s per round)
2. Code execution (0.5-5s depending on complexity)
3. File I/O (negligible)
4. Network latency (negligible for local vLLM)

### Optimization Strategies

1. **Reduce Rounds**
   - Better prompting
   - Provide more context upfront
   - Use few-shot examples

2. **Faster Execution**
   - Pre-import common libraries
   - Cache data loading
   - Use compiled code where possible

3. **Parallel Processing**
   - Multiple workers for concurrent requests
   - Async execution throughout
   - Queue-based architecture

---

## Debugging Tips

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In execute_code:
print(f"Executing code:\n{code_str}")
print(f"Output:\n{output}")
```

### Save Intermediate Results

```python
# In generate loop:
with open(f'round_{round_idx}_request.json', 'w') as f:
    json.dump(messages, f, indent=2)

with open(f'round_{round_idx}_response.txt', 'w') as f:
    f.write(ans)
```

### Inspect Workspace

```python
# After execution:
print("Workspace contents:")
for root, dirs, files in os.walk(workspace_dir):
    for file in files:
        print(os.path.join(root, file))
```

---

## Summary

The `generate()` and `execute_code()` methods form the core of DeepAnalyze's autonomous capabilities:

1. **Multi-round reasoning** - Model can iterate and refine
2. **Code execution** - Real Python code runs in workspace
3. **Feedback loops** - Execution results inform next steps
4. **File tracking** - Generated artifacts are captured
5. **Error handling** - Failures are reported back to model

This architecture enables the model to:
- Explore data iteratively
- Fix errors in its own code
- Generate complex multi-step analyses
- Create visualizations and reports
- Adapt to unexpected data formats

The key insight is that the model doesn't need to be perfect on the first try - it can observe, learn, and improve through multiple rounds of execution.
