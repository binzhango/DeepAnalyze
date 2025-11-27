# DeepAnalyze Training Process - Comprehensive Summary

## Overview

DeepAnalyze uses a **3-stage curriculum-based training approach** to transform a base reasoning model into an autonomous data science agent. The training process is called "Curriculum-based Agentic Training" and progressively builds capabilities from single-task reasoning to multi-turn autonomous execution.

---

## Training Pipeline Architecture

```
Stage 0: Vocabulary Extension
    ↓
Stage 1: Single-Ability Fine-tuning (SFT)
    ↓
Stage 2: Multi-Ability Cold Start (SFT)
    ↓
Stage 3: Reinforcement Learning (RL)
    ↓
Final Model: DeepAnalyze-8B
```

---

## Stage 0: Vocabulary Extension

### Purpose
Add special tokens for structured output to the base model's vocabulary.

### Base Model
**DeepSeek-R1-0528-Qwen3-8B**
- 8 billion parameters
- Pre-trained reasoning model
- Strong code generation capabilities

### Process

**Script:** `deepanalyze/add_vocab.py`

**New Tokens Added:**
```python
new_tokens = [
    "<Analyze>",      # Analysis section
    "</Analyze>",
    "<Understand>",   # Understanding section
    "</Understand>",
    "<Code>",         # Code to execute
    "</Code>",
    "<Execute>",      # Execution results
    "</Execute>",
    "<Answer>",       # Final answer
    "</Answer>",
]
```

**Implementation:**
1. Load base model and tokenizer
2. Add 10 new tokens to vocabulary
3. Resize model embeddings to accommodate new tokens
4. Initialize new token embeddings (randomly or from similar tokens)
5. Save extended model

**Command:**
```bash
python deepanalyze/add_vocab.py \
  --model_path DeepSeek-R1-0528-Qwen3-8B \
  --save_path DeepSeek-R1-0528-Qwen3-8B-AddVocab \
  --add_tags
```

**Why This Matters:**
- Enables structured output parsing
- Allows model to signal different reasoning stages
- Facilitates code extraction and execution
- Provides clear boundaries for multi-turn interaction

---

## Stage 1: Single-Ability Fine-tuning

### Purpose
Teach the model individual data science skills through supervised fine-tuning.

### Training Framework
**ms-swift** (ModelScope Swift)
- Efficient fine-tuning framework
- Supports DeepSpeed ZeRO-3 for distributed training
- Flash Attention for memory efficiency

### Dataset Composition

**Total:** ~421,060 examples

#### Reasoning Tasks (320,060 examples)
1. **SKGInstruct** (199,989) - Structured knowledge grounding
2. **TableQA Distillation** (39,301) - Table question answering
3. **TableQA Refinement** (39,301) - Refined table QA
4. **TableGPT** (29,448) - Table understanding and generation

#### File Processing (13,023 examples)
5. **Database Files** (3,833) - SQL and database operations
6. **CSV Files** (3,007) - CSV data processing
7. **Excel Files** (3,663) - XLSX file handling
8. **Other Files** (2,520) - JSON, XML, TXT, etc.

#### General Capabilities (87,998 examples)
9. **Math** (20,000) - Mathematical reasoning
10. **Code** (20,000) - Code generation and debugging
11. **Science** (20,000) - Scientific analysis
12. **Instruction Following** (20,000) - General instructions
13. **Other** (19,998) - Miscellaneous tasks

### Training Configuration

**Hardware:**
- 8 GPUs (CUDA devices 0-7)
- DeepSpeed ZeRO-3 for memory optimization
- Flash Attention for efficient attention computation

**Hyperparameters:**
```bash
--num_train_epochs 3
--per_device_train_batch_size 8
--gradient_accumulation_steps 4
--learning_rate 5e-5
--max_length 8192
--warmup_ratio 0.05
--torch_dtype bfloat16
```

**Effective Batch Size:**
```
8 GPUs × 8 samples × 4 accumulation = 256 samples per update
```

**Optimization:**
- **DeepSpeed ZeRO-3**: Partitions optimizer states, gradients, and parameters
- **Liger Kernel**: Optimized CUDA kernels for faster training
- **Flash Attention**: Memory-efficient attention mechanism
- **Packing**: Combines multiple sequences to maximize GPU utilization

**Training Time:** ~3 days on 8× A100 GPUs

### Output
**Model:** Single-ability checkpoint with strong individual task performance

---

## Stage 2: Multi-Ability Cold Start

### Purpose
Teach the model to perform **multi-turn autonomous execution** - the ability to generate code, observe results, and iterate.

### Key Difference from Stage 1
- Stage 1: Single-turn responses
- Stage 2: Multi-turn iterative problem solving

### Dataset Composition

**Total:** ~26,202 examples

#### Data Pipeline Tasks (8,528 examples)
1. **Data Pipeline** (3,601) - End-to-end data workflows
2. **Data Preparation** (3,311) - Data loading and preprocessing
3. **Data Cleaning** (1,616) - Data quality and cleaning

#### Data Analysis Tasks (4,998 examples)
4. **Data Analysis** (3,936) - Statistical analysis
5. **Data Insight** (1,062) - Pattern discovery and insights

#### Research Tasks (12,676 examples)
6. **Research Database** (818) - Database-driven research
7. **Research XLSX** (848) - Excel-based research
8. **Research Other** (3,505) - Various data sources
9. **Research Data Preparation** (488) - Research data prep
10. **Research Data Analysis** (1,339) - Research analysis
11. **Research Data Insight** (1,351) - Research insights
12. **Research Report Generation** (4,327) - Report writing

### Training Configuration

**Key Changes from Stage 1:**
```bash
--model "${MODEL_SINGLE_ABILITY_PATH}"  # Start from Stage 1
--learning_rate 5e-6                     # Lower LR (10x smaller)
--per_device_train_batch_size 1         # Smaller batch (longer sequences)
--gradient_accumulation_steps 32        # More accumulation
--max_length 32768                      # 4x longer context (8192 → 32768)
```

**Why Lower Learning Rate?**
- Preserve single-ability knowledge
- Fine-tune multi-turn behavior
- Avoid catastrophic forgetting

**Why Longer Context?**
- Multi-turn conversations are longer
- Need to track execution history
- Enable complex iterative reasoning

**Effective Batch Size:**
```
8 GPUs × 1 sample × 32 accumulation = 256 samples per update
```

**Training Time:** ~2 days on 8× A100 GPUs

### Output
**Model:** Multi-ability checkpoint capable of autonomous iteration

---

## Stage 3: Reinforcement Learning

### Purpose
Optimize the model's autonomous behavior through **trial and error** in real execution environments.

### Training Framework
**SkyRL** (Sky Reinforcement Learning)
- Custom RL framework for LLMs
- Supports GRPO (Group Relative Policy Optimization)
- Integrated with vLLM for fast inference

### Algorithm: GRPO
**Group Relative Policy Optimization**
- Variant of PPO (Proximal Policy Optimization)
- Groups samples for relative advantage estimation
- More stable than vanilla PPO for LLMs
- No separate value network needed

### Environment: DeepAnalyze Gym

**Custom RL Environment:**
```python
environment.env_class="deepanalyze"
environment.skyrl_gym.deepanalyze.workspace="${DATA_DIR}/RL/data/"
```

**How It Works:**
1. Model generates code
2. Code executes in real workspace
3. Reward based on:
   - Task completion
   - Code correctness
   - Execution success
   - Output quality
   - Number of iterations

### Dataset Composition

**Total:** 3 Parquet files with diverse tasks

1. **QA Tasks** (`qa.parquet`)
   - Question answering over data
   - Requires data loading and analysis

2. **Data Tasks** (`datatask.parquet`)
   - Specific data science tasks
   - Cleaning, transformation, visualization

3. **Research Tasks** (`research.parquet`)
   - Open-ended research questions
   - Report generation

### Training Configuration

**RL-Specific Parameters:**
```bash
trainer.algorithm.advantage_estimator="grpo"
trainer.train_batch_size=256
trainer.policy.optimizer_config.lr=5e-7  # Even lower LR
generator.n_samples_per_prompt=5         # 5 rollouts per prompt
generator.max_turns=30                   # Up to 30 iterations
trainer.algorithm.use_kl_loss=false      # No KL penalty
```

**Generation Parameters:**
```bash
generator.sampling_params.temperature=0.0     # Greedy (deterministic)
generator.sampling_params.top_p=0.95
generator.sampling_params.stop_token_ids="[151676,151645]"  # Stop tokens
generator.sampling_params.max_generate_length=32768
```

**Infrastructure:**
```bash
generator.num_inference_engines=8        # 8 vLLM engines
generator.inference_engine_tensor_parallel_size=1
generator.backend="vllm"                 # Use vLLM for speed
generator.async_engine=true              # Async generation
generator.batched=false                  # Sequential execution
```

**Memory Management:**
```bash
trainer.policy.fsdp_config.cpu_offload=true  # Offload to CPU
trainer.ref.fsdp_config.cpu_offload=true     # Reference model to CPU
generator.gpu_memory_utilization=0.5         # 50% GPU for inference
```

### RL Training Loop

```
For each epoch:
    For each batch of prompts:
        1. Generate 5 rollouts per prompt (n_samples=5)
        2. Execute code in real workspace
        3. Compute rewards based on outcomes
        4. Estimate advantages using GRPO
        5. Update policy with PPO-style objective
        6. Sync weights across GPUs
```

### Reward Function

**Components:**
1. **Task Completion** (0-1): Did it solve the task?
2. **Code Quality** (0-1): Is the code correct and efficient?
3. **Execution Success** (0-1): Did code run without errors?
4. **Output Quality** (0-1): Is the output useful?
5. **Efficiency** (0-1): Number of iterations (fewer is better)

**Total Reward:**
```
reward = w1*completion + w2*quality + w3*success + w4*output + w5*efficiency
```

### Training Time
**~5-7 days on 8× A100 GPUs**

### Output
**Model:** DeepAnalyze-8B - Final production model

---

## Complete Training Timeline

```
Stage 0: Vocabulary Extension
├─ Time: ~1 hour
├─ Resources: 1 GPU
└─ Output: Extended base model

Stage 1: Single-Ability SFT
├─ Time: ~3 days
├─ Resources: 8× A100 GPUs
├─ Data: 421K examples
└─ Output: Single-ability checkpoint

Stage 2: Multi-Ability Cold Start
├─ Time: ~2 days
├─ Resources: 8× A100 GPUs
├─ Data: 26K examples
└─ Output: Multi-ability checkpoint

Stage 3: Reinforcement Learning
├─ Time: ~5-7 days
├─ Resources: 8× A100 GPUs
├─ Data: 3 parquet files
└─ Output: DeepAnalyze-8B (final)

Total: ~10-12 days on 8× A100 GPUs
```

---

## Training Data Summary

### Total Dataset: DataScience-Instruct-500K

**Source:** https://huggingface.co/datasets/RUC-DataLab/DataScience-Instruct-500K

**Composition:**
- **SFT Data**: ~447K examples
  - Reasoning tasks
  - File processing
  - General capabilities
  - Multi-turn interactions
- **RL Data**: ~50K+ rollouts
  - QA tasks
  - Data tasks
  - Research tasks

**Data Sources:**
1. **Reasoning-Table**: Table reasoning tasks
2. **Spider**: SQL and database tasks
3. **BIRD**: Complex database reasoning
4. **DABStep**: Data analysis benchmarks
5. **Synthetic**: Generated by GPT-4/Claude

---

## Key Training Innovations

### 1. Curriculum Learning
Progressive difficulty:
- Stage 1: Individual skills
- Stage 2: Multi-turn execution
- Stage 3: Autonomous optimization

### 2. Structured Output Training
Special tokens enable:
- Clear reasoning stages
- Code extraction
- Execution feedback
- Multi-turn dialogue

### 3. Real Execution Environment
RL training uses actual code execution:
- Real Python interpreter
- Real file system
- Real data files
- Real error messages

### 4. Multi-Turn Optimization
Unlike single-turn models:
- Learns to iterate
- Learns from execution results
- Learns to fix errors
- Learns when to stop

---

## Hardware Requirements

### Minimum (Inference Only)
- 1× GPU with 24GB VRAM (RTX 3090, A5000)
- 32GB RAM
- 100GB disk space

### Training Requirements

**Stage 1 & 2 (SFT):**
- 8× A100 80GB GPUs (recommended)
- 512GB RAM
- 2TB NVMe SSD
- High-speed interconnect (NVLink, InfiniBand)

**Stage 3 (RL):**
- 8× A100 80GB GPUs (required)
- 1TB RAM (for CPU offloading)
- 5TB NVMe SSD (for rollout storage)
- High-speed interconnect

### Cost Estimate
**Cloud Training (AWS p4d.24xlarge):**
- $32.77/hour × 8 GPUs = ~$262/hour
- 10-12 days = 240-288 hours
- **Total: ~$63,000 - $75,000**

---

## How to Reproduce Training

### Step 1: Prepare Environment
```bash
# Clone repository
git clone https://github.com/ruc-datalab/DeepAnalyze.git
cd DeepAnalyze

# Install dependencies
pip install -r requirements.txt

# Install training frameworks
cd deepanalyze/ms-swift && pip install -e .
cd ../SkyRL && pip install -e .
```

### Step 2: Download Data
```bash
# Download training data
huggingface-cli download RUC-DataLab/DataScience-Instruct-500K

# Unzip RL data
cd DataScience-Instruct-500K/RL
unzip data.zip
```

### Step 3: Download Base Model
```bash
# Download base model
huggingface-cli download deepseek-ai/DeepSeek-R1-0528-Qwen3-8B
```

### Step 4: Extend Vocabulary
```bash
python deepanalyze/add_vocab.py \
  --model_path DeepSeek-R1-0528-Qwen3-8B \
  --save_path DeepSeek-R1-0528-Qwen3-8B-AddVocab \
  --add_tags
```

### Step 5: Stage 1 Training
```bash
# Edit paths in scripts/single.sh
cd deepanalyze/ms-swift
bash ../../scripts/single.sh
```

### Step 6: Stage 2 Training
```bash
# Edit paths in scripts/multi_coldstart.sh
bash ../../scripts/multi_coldstart.sh
```

### Step 7: Stage 3 Training
```bash
# Edit paths in scripts/multi_rl.sh
cd ../SkyRL/skyrl-train
bash ../../scripts/multi_rl.sh
```

### Step 8: Export Final Model
```bash
# Model will be saved in FINAL_MODEL_PATH/export
# Upload to HuggingFace
huggingface-cli upload RUC-DataLab/DeepAnalyze-8B ./export
```

---

## Fine-tuning for Your Use Case

### Option 1: Continue SFT (Recommended)

**Use Case:** Add domain-specific knowledge

```bash
swift sft \
    --model "RUC-DataLab/DeepAnalyze-8B" \
    --train_type "lora" \
    --dataset "your_domain_data.json" \
    --num_train_epochs 3 \
    --learning_rate 1e-4 \
    --max_length 8192
```

**Data Format:**
```json
[
  {
    "messages": [
      {"role": "user", "content": "# Instruction\nAnalyze medical data\n\n# Data\nFile 1: ..."},
      {"role": "assistant", "content": "<Analyze>...</Analyze>\n<Code>...</Code>"}
    ]
  }
]
```

### Option 2: LoRA Fine-tuning

**Use Case:** Efficient adaptation with limited resources

```bash
swift sft \
    --model "RUC-DataLab/DeepAnalyze-8B" \
    --train_type "lora" \
    --lora_rank 64 \
    --lora_alpha 128 \
    --dataset "your_data.json" \
    --learning_rate 1e-4
```

**Benefits:**
- Only trains ~1% of parameters
- Requires 1-2 GPUs instead of 8
- Faster training (hours instead of days)
- Easy to merge back to base model

### Option 3: Domain-Specific RL

**Use Case:** Optimize for specific workflows

```bash
# Create custom environment
class YourDomainEnv(DeepAnalyzeEnv):
    def compute_reward(self, output):
        # Custom reward logic
        return reward

# Run RL training
python -m examples.your_domain.main \
    trainer.policy.model.path="RUC-DataLab/DeepAnalyze-8B" \
    environment.env_class="your_domain"
```

---

## Key Takeaways

### 1. Curriculum is Critical
Progressive training from simple to complex enables autonomous behavior.

### 2. Structured Output Matters
Special tokens enable reliable parsing and multi-turn interaction.

### 3. Real Execution is Essential
RL training with actual code execution teaches practical skills.

### 4. Multi-Turn is Different
Training for iteration requires different data and objectives than single-turn.

### 5. Scale is Important
8B parameters + extensive training data + RL = autonomous capabilities.

---

## Comparison with Other Approaches

### vs. Single-Turn Code Models (CodeLlama, StarCoder)
- ❌ They: Generate code once
- ✅ DeepAnalyze: Iterates until success

### vs. Agent Frameworks (AutoGPT, LangChain)
- ❌ They: Rely on prompting closed-source models
- ✅ DeepAnalyze: Trained end-to-end for autonomy

### vs. Tool-Using Models (Gorilla, ToolLLM)
- ❌ They: Call external tools
- ✅ DeepAnalyze: Generates and executes code directly

### vs. Data Analysis Tools (Pandas AI, Julius)
- ❌ They: Limited to specific workflows
- ✅ DeepAnalyze: Open-ended research and analysis

---

## Future Directions

### Potential Improvements
1. **Larger Models**: 70B, 405B parameters
2. **More Data**: 1M+ training examples
3. **Better RL**: More sophisticated reward functions
4. **Multi-Modal**: Support images, PDFs, videos
5. **Distributed Execution**: Multi-machine code execution
6. **Safety**: Sandboxing, security, privacy

### Research Questions
1. Can we reduce training time with better curricula?
2. Can we improve sample efficiency in RL?
3. Can we transfer to other domains (biology, finance)?
4. Can we make it work with smaller models (1B, 3B)?

---

## Resources

### Papers
- [DeepAnalyze Paper](https://arxiv.org/abs/2510.16872)
- [DeepSeek-R1 Paper](https://arxiv.org/abs/...)
- [GRPO Paper](https://arxiv.org/abs/...)

### Code
- [DeepAnalyze GitHub](https://github.com/ruc-datalab/DeepAnalyze)
- [ms-swift](https://github.com/modelscope/ms-swift)
- [SkyRL](https://github.com/NovaSky-AI/SkyRL)

### Models & Data
- [DeepAnalyze-8B](https://huggingface.co/RUC-DataLab/DeepAnalyze-8B)
- [DataScience-Instruct-500K](https://huggingface.co/datasets/RUC-DataLab/DataScience-Instruct-500K)
- [Base Model](https://huggingface.co/deepseek-ai/DeepSeek-R1-0528-Qwen3-8B)

---

## Summary

DeepAnalyze's training process is a **sophisticated 3-stage curriculum** that transforms a reasoning model into an autonomous data science agent:

1. **Stage 1**: Learn individual skills (reasoning, coding, file processing)
2. **Stage 2**: Learn multi-turn execution (iteration, error recovery)
3. **Stage 3**: Optimize autonomous behavior (RL in real environments)

The key innovations are:
- Structured output with special tokens
- Progressive curriculum learning
- Real code execution in RL
- Multi-turn optimization

This approach enables DeepAnalyze to autonomously complete complex data science tasks through iterative code generation and execution.
