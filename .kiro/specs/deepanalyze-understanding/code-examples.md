# DeepAnalyze Code Examples

This document provides practical code examples showing how the `generate()` and `execute_code()` methods work in detail.

---

## Example 1: Basic Usage

### User Code
```python
from deepanalyze import DeepAnalyzeVLLM

# Initialize
deepanalyze = DeepAnalyzeVLLM(
    model_name="DeepAnalyze-8B",
    api_url="http://localhost:8000/v1/chat/completions",
    max_rounds=30
)

# Prepare prompt
prompt = """# Instruction
Analyze the sales data and create a visualization.

# Data
File 1: {"name": "sales.csv", "size": "5.2KB"}
"""

# Generate
result = deepanalyze.generate(
    prompt=prompt,
    workspace="/path/to/workspace",
    temperature=0.5
)

print(result["reasoning"])
```

---

## Example 2: Step-by-Step Execution Trace

### Initial State
```python
# Workspace before execution
workspace/
└── sales.csv

# Messages
messages = [
    {"role": "user", "content": "Analyze sales.csv"}
]
```

### Round 1: Data Loading

**Model Response:**
```
<Analyze>
I need to load the CSV file and examine its structure to understand what data we're working with.
</Analyze>

<Code>
```python
import pandas as pd

# Load the data
df = pd.read_csv('sales.csv')

# Display basic information
print("Dataset shape:", df.shape)
print("\nColumn names:", df.columns.tolist())
print("\nFirst 5 rows:")
print(df.head())
print("\nData types:")
print(df.dtypes)
print("\nBasic statistics:")
print(df.describe())
```
</Code>
```

**Code Extraction:**
```python
code_match = re.search(r"<Code>(.*?)</Code>", response, re.DOTALL)
# Matches: ```python\nimport pandas...\n```

md_match = re.search(r"```(?:python)?(.*?)```", code_content, re.DOTALL)
# Extracts: import pandas as pd\n\ndf = pd.read_csv...
```

**Execution:**
```python
exe_output = self.execute_code(code_str)
```

**Output:**
```
Dataset shape: (100, 4)

Column names: ['date', 'product', 'quantity', 'revenue']

First 5 rows:
         date product  quantity  revenue
0  2024-01-01   Apple        10    150.0
1  2024-01-01  Banana        15    120.0
2  2024-01-02   Apple         8    120.0
3  2024-01-02  Orange        12    180.0
4  2024-01-03  Banana        20    160.0

Data types:
date        object
product     object
quantity     int64
revenue    float64
dtype: object

Basic statistics:
         quantity      revenue
count  100.000000   100.000000
mean    12.500000   156.250000
std      4.123106    51.234567
min      5.000000    75.000000
25%      9.000000   112.500000
50%     12.500000   150.000000
75%     15.000000   187.500000
max     20.000000   300.000000
```

**Messages Updated:**
```python
messages = [
    {"role": "user", "content": "Analyze sales.csv"},
    {"role": "assistant", "content": "<Analyze>...</Analyze>\n<Code>...</Code>"},
    {"role": "execute", "content": "Dataset shape: (100, 4)\n..."}
]
```

---

### Round 2: Data Analysis

**Model Response (sees previous output):**
```
<Understand>
Based on the data exploration, I can see:
- 100 sales records
- 4 columns: date, product, quantity, revenue
- Date needs to be converted to datetime
- Products include Apple, Banana, Orange
- Revenue ranges from $75 to $300

I'll now calculate key metrics and prepare for visualization.
</Understand>

<Code>
```python
import pandas as pd

# Load and prepare data
df = pd.read_csv('sales.csv')
df['date'] = pd.to_datetime(df['date'])

# Calculate metrics
total_revenue = df['revenue'].sum()
avg_revenue = df['revenue'].mean()

# Group by product
product_revenue = df.groupby('product')['revenue'].sum().sort_values(ascending=False)
product_quantity = df.groupby('product')['quantity'].sum().sort_values(ascending=False)

print("=== Sales Analysis ===")
print(f"\nTotal Revenue: ${total_revenue:,.2f}")
print(f"Average Revenue per Sale: ${avg_revenue:,.2f}")
print(f"\nRevenue by Product:")
print(product_revenue)
print(f"\nQuantity Sold by Product:")
print(product_quantity)

# Calculate daily trends
daily_revenue = df.groupby('date')['revenue'].sum()
print(f"\nDaily Revenue Trend:")
print(f"  Highest: ${daily_revenue.max():,.2f} on {daily_revenue.idxmax().date()}")
print(f"  Lowest: ${daily_revenue.min():,.2f} on {daily_revenue.idxmin().date()}")
```
</Code>
```

**Execution Output:**
```
=== Sales Analysis ===

Total Revenue: $15,625.00
Average Revenue per Sale: $156.25

Revenue by Product:
product
Apple     5,250.00
Banana    4,800.00
Orange    5,575.00
Name: revenue, dtype: float64

Quantity Sold by Product:
product
Banana    420
Apple     350
Orange    480
Name: quantity, dtype: int64

Daily Revenue Trend:
  Highest: $850.00 on 2024-01-15
  Lowest: $120.00 on 2024-01-03
```

**Messages Updated:**
```python
messages = [
    {"role": "user", "content": "Analyze sales.csv"},
    {"role": "assistant", "content": "<Analyze>...</Analyze>\n<Code>...</Code>"},
    {"role": "execute", "content": "Dataset shape: (100, 4)\n..."},
    {"role": "assistant", "content": "<Understand>...</Understand>\n<Code>...</Code>"},
    {"role": "execute", "content": "=== Sales Analysis ===\n..."}
]
```

---

### Round 3: Visualization

**Model Response:**
```
<Code>
```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load and prepare data
df = pd.read_csv('sales.csv')
df['date'] = pd.to_datetime(df['date'])
df['total_sales'] = df['quantity'] * df['revenue']

# Create figure with subplots
fig, axes = plt.subplots(2, 2, figsize=(15, 12))
fig.suptitle('Sales Analysis Dashboard', fontsize=16, fontweight='bold')

# 1. Revenue by Product (Bar Chart)
product_revenue = df.groupby('product')['revenue'].sum().sort_values(ascending=False)
axes[0, 0].bar(product_revenue.index, product_revenue.values, color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
axes[0, 0].set_title('Total Revenue by Product', fontsize=12, fontweight='bold')
axes[0, 0].set_ylabel('Revenue ($)')
axes[0, 0].grid(axis='y', alpha=0.3)

# 2. Quantity Sold by Product (Horizontal Bar)
product_quantity = df.groupby('product')['quantity'].sum().sort_values()
axes[0, 1].barh(product_quantity.index, product_quantity.values, color=['#95E1D3', '#F38181', '#AA96DA'])
axes[0, 1].set_title('Total Quantity Sold by Product', fontsize=12, fontweight='bold')
axes[0, 1].set_xlabel('Quantity')
axes[0, 1].grid(axis='x', alpha=0.3)

# 3. Daily Revenue Trend (Line Chart)
daily_revenue = df.groupby('date')['revenue'].sum()
axes[1, 0].plot(daily_revenue.index, daily_revenue.values, marker='o', linewidth=2, markersize=4)
axes[1, 0].set_title('Daily Revenue Trend', fontsize=12, fontweight='bold')
axes[1, 0].set_xlabel('Date')
axes[1, 0].set_ylabel('Revenue ($)')
axes[1, 0].tick_params(axis='x', rotation=45)
axes[1, 0].grid(alpha=0.3)

# 4. Product Distribution (Pie Chart)
product_counts = df['product'].value_counts()
axes[1, 1].pie(product_counts.values, labels=product_counts.index, autopct='%1.1f%%',
               colors=['#FF6B6B', '#4ECDC4', '#45B7D1'], startangle=90)
axes[1, 1].set_title('Sales Distribution by Product', fontsize=12, fontweight='bold')

plt.tight_layout()
plt.savefig('sales_dashboard.png', dpi=300, bbox_inches='tight')
print("✓ Dashboard saved as 'sales_dashboard.png'")

# Also create a detailed report
plt.figure(figsize=(12, 8))
sns.boxplot(data=df, x='product', y='revenue', palette='Set2')
plt.title('Revenue Distribution by Product', fontsize=14, fontweight='bold')
plt.ylabel('Revenue ($)')
plt.xlabel('Product')
plt.grid(axis='y', alpha=0.3)
plt.savefig('revenue_distribution.png', dpi=300, bbox_inches='tight')
print("✓ Revenue distribution saved as 'revenue_distribution.png'")
```
</Code>
```

**Execution Output:**
```
✓ Dashboard saved as 'sales_dashboard.png'
✓ Revenue distribution saved as 'revenue_distribution.png'
```

**Workspace After Execution:**
```
workspace/
├── sales.csv
├── sales_dashboard.png          # NEW
└── revenue_distribution.png     # NEW
```

**File Tracking:**
```python
tracker = WorkspaceTracker(workspace, generated_dir)
artifacts = tracker.diff_and_collect()
# Returns: [
#   Path("generated/sales_dashboard.png"),
#   Path("generated/revenue_distribution.png")
# ]
```

---

### Round 4: Final Answer

**Model Response:**
```
<Answer>
# Sales Analysis Report

## Executive Summary
I've completed a comprehensive analysis of the sales data (100 records). Here are the key findings:

## Key Metrics
- **Total Revenue**: $15,625.00
- **Average Revenue per Sale**: $156.25
- **Date Range**: January 1-31, 2024

## Product Performance

### Revenue Leaders
1. **Orange**: $5,575.00 (35.7%)
2. **Apple**: $5,250.00 (33.6%)
3. **Banana**: $4,800.00 (30.7%)

### Volume Leaders
1. **Orange**: 480 units
2. **Banana**: 420 units
3. **Apple**: 350 units

## Trends
- **Peak Sales Day**: January 15, 2024 ($850.00)
- **Lowest Sales Day**: January 3, 2024 ($120.00)
- Revenue shows moderate daily variation with an upward trend

## Visualizations Created
1. **sales_dashboard.png** - Comprehensive 4-panel dashboard showing:
   - Revenue by product (bar chart)
   - Quantity sold by product (horizontal bar)
   - Daily revenue trend (line chart)
   - Product distribution (pie chart)

2. **revenue_distribution.png** - Box plot showing revenue distribution by product

## Recommendations
1. **Focus on Orange**: Highest revenue and volume - consider expanding inventory
2. **Investigate January 3**: Understand why sales were lowest to prevent future dips
3. **Capitalize on Trends**: The upward trend suggests growing demand - prepare for scaling

All visualizations have been saved and are ready for presentation.
</Answer>
```

**Loop Terminates** because `<Answer>` tag is found.

**Final Result:**
```python
result = {
    "reasoning": """
<Analyze>
I need to load the CSV file...
</Analyze>

<Code>
```python
import pandas as pd
...
```
</Code>

<Execute>
Dataset shape: (100, 4)
...
</Execute>

<Understand>
Based on the data exploration...
</Understand>

<Code>
```python
import pandas as pd
...
```
</Code>

<Execute>
=== Sales Analysis ===
...
</Execute>

<Code>
```python
import pandas as pd
import matplotlib.pyplot as plt
...
```
</Code>

<Execute>
✓ Dashboard saved as 'sales_dashboard.png'
✓ Revenue distribution saved as 'revenue_distribution.png'
</Execute>

<Answer>
# Sales Analysis Report
...
</Answer>
"""
}
```

---

## Example 3: Error Handling

### Code with Error

**Model Generates:**
```python
<Code>
```python
import pandas as pd

df = pd.read_csv('nonexistent.csv')  # File doesn't exist!
print(df.head())
```
</Code>
```

**Execution:**
```python
exe_output = self.execute_code(code_str)
```

**Output:**
```
[Error]:
Traceback (most recent call last):
  File "<string>", line 3, in <module>
    df = pd.read_csv('nonexistent.csv')
FileNotFoundError: [Errno 2] No such file or directory: 'nonexistent.csv'
```

**Model Sees Error and Fixes:**
```
<Understand>
I see the error - the file doesn't exist. Let me check what files are available in the workspace.
</Understand>

<Code>
```python
import os

print("Files in workspace:")
for file in os.listdir('.'):
    if os.path.isfile(file):
        print(f"  - {file}")
```
</Code>
```

**Execution:**
```
Files in workspace:
  - sales.csv
  - data.xlsx
```

**Model Corrects:**
```
<Understand>
I see! The file is named 'sales.csv', not 'nonexistent.csv'. Let me load the correct file.
</Understand>

<Code>
```python
import pandas as pd

df = pd.read_csv('sales.csv')  # Correct filename
print(df.head())
```
</Code>
```

**Success!**

---

## Example 4: execute_code() Implementation Details

### Basic Implementation (deepanalyze.py)

```python
def execute_code(self, code_str: str) -> str:
    """
    Executes Python code and captures stdout and stderr outputs.
    Returns the output or formatted error message.
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        # Redirect stdout and stderr
        with contextlib.redirect_stdout(stdout_capture), \
             contextlib.redirect_stderr(stderr_capture):
            # Execute code with empty globals (isolation)
            exec(code_str, {})
        
        # Collect output
        output = stdout_capture.getvalue()
        if stderr_capture.getvalue():
            output += stderr_capture.getvalue()
        
        return output
    
    except Exception as exec_error:
        # Format error message
        code_lines = code_str.splitlines()
        tb_lines = traceback.format_exc().splitlines()
        error_line = None

        # Find line number
        for line in tb_lines:
            if 'File "<string>", line' in line:
                try:
                    line_num = int(line.split(", line ")[1].split(",")[0])
                    error_line = line_num
                    break
                except (IndexError, ValueError):
                    continue

        # Build error message
        error_message = "Traceback (most recent call last):\n"
        if error_line and 1 <= error_line <= len(code_lines):
            error_message += f'  File "<string>", line {error_line}, in <module>\n'
            error_message += f"    {code_lines[error_line - 1].strip()}\n"
        error_message += f"{type(exec_error).__name__}: {str(exec_error)}"
        
        if stderr_capture.getvalue():
            error_message += f"\n{stderr_capture.getvalue()}"
        
        return f"[Error]:\n{error_message.strip()}"
```

### Example Execution

**Input Code:**
```python
code_str = """
import pandas as pd

data = {'A': [1, 2, 3], 'B': [4, 5, 6]}
df = pd.DataFrame(data)
print(df)
print("Sum of A:", df['A'].sum())
"""
```

**Execution:**
```python
output = execute_code(code_str)
```

**Output:**
```
   A  B
0  1  4
1  2  5
2  3  6
Sum of A: 6
```

---

## Example 5: Advanced Execution (API Server)

### Subprocess Implementation (API/utils.py)

```python
def execute_code_safe(
    code_str: str, 
    workspace_dir: str, 
    timeout_sec: int = 120
) -> str:
    """Execute Python code in a separate process with timeout"""
    
    # Get absolute path
    exec_cwd = os.path.abspath(workspace_dir)
    os.makedirs(exec_cwd, exist_ok=True)
    tmp_path = None
    
    try:
        # Create temporary Python file
        fd, tmp_path = tempfile.mkstemp(suffix=".py", dir=exec_cwd)
        os.close(fd)
        
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(code_str)

        # Configure environment
        child_env = os.environ.copy()
        child_env.setdefault("MPLBACKEND", "Agg")  # Headless matplotlib
        child_env.setdefault("QT_QPA_PLATFORM", "offscreen")  # Headless Qt
        child_env.pop("DISPLAY", None)  # No display

        # Execute in subprocess
        completed = subprocess.run(
            [sys.executable, tmp_path],
            cwd=exec_cwd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            env=child_env,
        )
        
        # Combine stdout and stderr
        output = (completed.stdout or "") + (completed.stderr or "")
        return output
    
    except subprocess.TimeoutExpired:
        return f"[Timeout]: execution exceeded {timeout_sec} seconds"
    
    except Exception as e:
        return f"[Error]: {str(e)}"
    
    finally:
        # Cleanup temporary file
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
```

### Example with Matplotlib

**Input Code:**
```python
code_str = """
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(10, 6))
plt.plot(x, y)
plt.title('Sine Wave')
plt.xlabel('X')
plt.ylabel('Y')
plt.grid(True)
plt.savefig('sine_wave.png')
print("Plot saved successfully!")
"""
```

**Execution:**
```python
output = execute_code_safe(code_str, "/path/to/workspace")
```

**Output:**
```
Plot saved successfully!
```

**Files Created:**
```
workspace/
└── sine_wave.png  # NEW FILE
```

---

## Example 6: Async Execution

### Async Implementation

```python
async def execute_code_safe_async(
    code_str: str, 
    workspace_dir: str, 
    timeout_sec: int = 120
) -> str:
    """Execute Python code in a separate process with timeout (async version)"""
    
    exec_cwd = os.path.abspath(workspace_dir)
    os.makedirs(exec_cwd, exist_ok=True)
    tmp_path = None
    
    try:
        # Create temporary file
        fd, tmp_path = tempfile.mkstemp(suffix=".py", dir=exec_cwd)
        os.close(fd)
        
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(code_str)

        # Configure environment
        child_env = os.environ.copy()
        child_env.setdefault("MPLBACKEND", "Agg")
        child_env.setdefault("QT_QPA_PLATFORM", "offscreen")
        child_env.pop("DISPLAY", None)

        # Create async subprocess
        process = await asyncio.create_subprocess_exec(
            sys.executable, tmp_path,
            cwd=exec_cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=child_env,
        )

        try:
            # Wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_sec
            )
            
            output = (stdout.decode() if stdout else "") + \
                     (stderr.decode() if stderr else "")
            return output
        
        except asyncio.TimeoutError:
            # Kill process on timeout
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass
            return f"[Timeout]: execution exceeded {timeout_sec} seconds"
    
    except Exception as e:
        return f"[Error]: {str(e)}"
    
    finally:
        # Cleanup
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
```

### Usage in FastAPI

```python
@router.post("/v1/chat/completions")
async def chat_completions(...):
    # ... setup code ...
    
    # Execute code asynchronously
    exe_output = await execute_code_safe_async(code_str, workspace_dir)
    
    # ... continue processing ...
```

---

## Example 7: Complete API Request Flow

### Client Request

```python
import requests

# Upload file
with open('sales.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:8200/v1/files',
        files={'file': f}
    )
file_id = response.json()['id']

# Chat request
response = requests.post(
    'http://localhost:8200/v1/chat/completions',
    json={
        'model': 'DeepAnalyze-8B',
        'messages': [{
            'role': 'user',
            'content': 'Analyze sales trends and create visualizations',
            'file_ids': [file_id]
        }],
        'temperature': 0.4
    }
)

result = response.json()
print(result['choices'][0]['message']['content'])

# Download generated files
for file_info in result['choices'][0]['message'].get('files', []):
    print(f"Download: {file_info['url']}")
```

### Server Processing

```python
# 1. Create thread workspace
thread = storage.create_thread()
workspace = get_thread_workspace(thread.id)

# 2. Copy files
shutil.copy(file_path, workspace / 'sales.csv')

# 3. Build prompt
vllm_messages = prepare_vllm_messages(messages, workspace)
# Result:
# [{
#   "role": "user",
#   "content": "# Instruction\nAnalyze sales trends...\n\n# Data\nFile 1: {\"name\": \"sales.csv\", \"size\": \"5.2KB\"}"
# }]

# 4. Multi-round execution
tracker = WorkspaceTracker(workspace, generated_dir)

while not finished:
    # Call vLLM
    response = vllm_client.chat.completions.create(...)
    
    # Extract code
    code = extract_code_from_segment(response)
    
    if code:
        # Execute
        output = await execute_code_safe_async(code, workspace)
        
        # Track files
        artifacts = tracker.diff_and_collect()
        
        # Build file URLs
        for artifact in artifacts:
            url = build_download_url(thread.id, artifact.name)
            generated_files.append({"name": artifact.name, "url": url})
        
        # Continue loop
        vllm_messages.append({"role": "execute", "content": output})
    else:
        finished = True

# 5. Return response
return {
    "choices": [{
        "message": {
            "content": full_response,
            "files": generated_files
        }
    }]
}
```

---

## Summary

The `generate()` and `execute_code()` methods work together to create an autonomous agent that can:

1. **Generate code** based on user requests
2. **Execute code** in isolated environments
3. **Observe results** (output, errors, files)
4. **Iterate** until task completion
5. **Track artifacts** automatically
6. **Handle errors** gracefully

This architecture enables DeepAnalyze to solve complex data science tasks through iterative refinement, just like a human data scientist would.
