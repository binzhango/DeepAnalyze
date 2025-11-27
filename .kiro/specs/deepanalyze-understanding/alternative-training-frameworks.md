# Alternative Training Frameworks Analysis

## Overview

This document analyzes the feasibility of using **Unsloth** or **Axolotl** instead of **ms-swift** for fine-tuning DeepAnalyze, covering compatibility, performance, features, and migration strategies.

---

## Current Framework: ms-swift

### What is ms-swift?
**ModelScope Swift** - Alibaba's training framework
- Part of ModelScope ecosystem
- Optimized for Chinese models
- Integrated with DeepSpeed
- Custom features for specific model architectures

### Why DeepAnalyze Uses It
1. **DeepSeek-R1 Support** - Native support for DeepSeek models
2. **Custom Model Type** - `model_type="deepseek_r1_distill"`
3. **Sequence Packing** - Efficient training with variable-length sequences
4. **DeepSpeed Integration** - ZeRO-3 optimization
5. **Liger Kernel** - Custom CUDA kernels

### Current Configuration
```bash
swift sft \
    --model_type "deepseek_r1_distill" \
    --train_type "full" \
    --packing true \
    --deepspeed "zero3" \
    --use_liger_kernel true \
    --attn_impl "flash_attn"
```

---

## Alternative 1: Unsloth

### What is Unsloth?
**Ultra-fast fine-tuning framework** by Daniel Han
- 2-5x faster than standard training
- 80% less memory usage
- Optimized kernels for LoRA/QLoRA
- Focus on efficiency and speed

### Official Repository
https://github.com/unslothai/unsloth

### Key Features

#### ✅ Advantages
1. **Speed** - 2-5x faster than HuggingFace Trainer
2. **Memory Efficiency** - 80% less VRAM usage
3. **Easy to Use** - Simple API, minimal configuration
4. **LoRA/QLoRA Optimized** - Best for parameter-efficient fine-tuning
5. **Free & Open Source** - Apache 2.0 license
6. **Active Development** - Regular updates and improvements
7. **Great Documentation** - Excellent examples and tutorials

#### ❌ Limitations
1. **LoRA Focus** - Primarily designed for LoRA, not full fine-tuning
2. **Limited Model Support** - Focused on popular architectures (Llama, Mistral, Qwen)
3. **No Native DeepSeek-R1 Support** - Would need custom implementation
4. **Single GPU Optimization** - Multi-GPU support is basic
5. **No DeepSpeed Integration** - Uses custom optimizations instead
6. **No Sequence Packing** - (as of current version)

### Compatibility Analysis

#### Model Architecture
```python
# DeepAnalyze is based on Qwen3
# Unsloth supports Qwen2, but Qwen3 support is uncertain

from unsloth import FastLanguageModel

# This might work:
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="RUC-DataLab/DeepAnalyze-8B",
    max_seq_length=32768,
    dtype=None,  # Auto-detect
    load_in_4bit=False,  # For full fine-tuning
)

# Add LoRA adapters
model = FastLanguageModel.get_peft_model(
    model,
    r=64,  # LoRA rank
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_alpha=128,
    lora_dropout=0.05,
    bias="none",
)
```

#### Training Configuration
```python
from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=32768,
    args=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=10,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=1,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        output_dir="outputs",
    ),
)
```

### Migration Strategy for Unsloth

#### ✅ Feasible: LoRA Fine-tuning
**Use Case:** Domain adaptation, adding new capabilities

```python
# unsloth_finetune.py

from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
import torch

# Load model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="RUC-DataLab/DeepAnalyze-8B",
    max_seq_length=32768,
    dtype=None,
    load_in_4bit=False,
)

# Add LoRA
model = FastLanguageModel.get_peft_model(
    model,
    r=64,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_alpha=128,
    lora_dropout=0.05,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=3407,
)

# Prepare dataset
dataset = load_dataset("json", data_files="your_data.json")

# Train
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=32768,
    args=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_ratio=0.05,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=1,
        optim="adamw_8bit",
        output_dir="outputs",
        save_strategy="epoch",
    ),
)

trainer.train()

# Save
model.save_pretrained("deepanalyze-lora")
tokenizer.save_pretrained("deepanalyze-lora")
```

#### ❌ Not Feasible: Full Fine-tuning (Stages 1-2)
**Reasons:**
- Unsloth optimized for LoRA, not full fine-tuning
- No sequence packing support
- Limited multi-GPU support
- No DeepSpeed integration
- Would lose speed advantages with full fine-tuning

#### ⚠️ Uncertain: Stage 3 (RL)
**Reasons:**
- Unsloth doesn't have RL training support
- Would still need SkyRL or similar
- Could potentially use Unsloth for policy model updates

### Performance Comparison

| Metric | ms-swift | Unsloth |
|--------|----------|---------|
| Full Fine-tuning Speed | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| LoRA Speed | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Memory Efficiency | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Multi-GPU Support | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Sequence Packing | ✅ | ❌ |
| DeepSpeed Support | ✅ | ❌ |
| Ease of Use | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### Recommendation for Unsloth

**✅ Use Unsloth for:**
- Domain-specific LoRA fine-tuning
- Quick experiments
- Single-GPU training
- Resource-constrained environments
- Adding new capabilities to existing model

**❌ Don't use Unsloth for:**
- Reproducing original training (Stages 1-2)
- Full fine-tuning from scratch
- Multi-GPU distributed training
- Training with sequence packing

---

## Alternative 2: Axolotl

### What is Axolotl?
**Comprehensive fine-tuning framework** by OpenAccess AI Collective
- Supports multiple training methods
- Extensive configuration options
- Production-ready
- Community-driven

### Official Repository
https://github.com/OpenAccess-AI-Collective/axolotl

### Key Features

#### ✅ Advantages
1. **Comprehensive** - Supports full fine-tuning, LoRA, QLoRA, FSDP, DeepSpeed
2. **Multi-GPU** - Excellent distributed training support
3. **Flexible Configuration** - YAML-based config system
4. **Wide Model Support** - Supports most HuggingFace models
5. **Production Ready** - Used by many organizations
6. **Active Community** - Large user base and contributors
7. **DeepSpeed Integration** - Full ZeRO support
8. **Sequence Packing** - Supported via `sample_packing: true`
9. **Flash Attention** - Built-in support

#### ❌ Limitations
1. **Complexity** - Steeper learning curve than Unsloth
2. **Configuration Heavy** - Requires detailed YAML configs
3. **Less Optimized** - Not as fast as Unsloth for LoRA
4. **Documentation** - Can be overwhelming for beginners
5. **DeepSeek-R1 Support** - May need custom model config

### Compatibility Analysis

#### Model Architecture
```yaml
# config.yaml

base_model: RUC-DataLab/DeepAnalyze-8B
model_type: qwen2  # Closest match, may need adjustment

# Tokenizer
tokenizer_type: AutoTokenizer
trust_remote_code: true

# Training
sequence_len: 32768
sample_packing: true
pad_to_sequence_len: true

# Flash Attention
flash_attention: true
s2_attention: false

# Adapter (for LoRA)
adapter: lora
lora_r: 64
lora_alpha: 128
lora_dropout: 0.05
lora_target_modules:
  - q_proj
  - k_proj
  - v_proj
  - o_proj
  - gate_proj
  - up_proj
  - down_proj
```

#### Training Configuration
```yaml
# Full Fine-tuning Config
output_dir: ./outputs

# Multi-GPU with DeepSpeed
deepspeed: deepspeed_configs/zero3.json
fsdp:
fsdp_config:

# Training params
num_epochs: 3
micro_batch_size: 8
gradient_accumulation_steps: 4
learning_rate: 5e-5
lr_scheduler: cosine
warmup_ratio: 0.05

# Optimization
bf16: true
fp16: false
tf32: true
gradient_checkpointing: true

# Logging
logging_steps: 1
save_steps: 50
eval_steps: 50

# Dataset
datasets:
  - path: data/reasoning/
    type: json
  - path: data/file_processing/
    type: json
```

### Migration Strategy for Axolotl

#### ✅ Feasible: Full Fine-tuning (Stages 1-2)
**Use Case:** Reproducing original training or custom full fine-tuning

**Step 1: Install Axolotl**
```bash
git clone https://github.com/OpenAccess-AI-Collective/axolotl
cd axolotl
pip install -e .
```

**Step 2: Create Config**
```yaml
# deepanalyze_stage1.yaml

base_model: DeepSeek-R1-0528-Qwen3-8B-AddVocab
model_type: qwen2
tokenizer_type: AutoTokenizer
trust_remote_code: true

# Training
sequence_len: 8192
sample_packing: true
pad_to_sequence_len: true

# Flash Attention
flash_attention: true
flash_attention_2: true

# DeepSpeed
deepspeed: deepspeed_configs/zero3.json

# Training params
num_epochs: 3
micro_batch_size: 8
gradient_accumulation_steps: 4
learning_rate: 5e-5
lr_scheduler: cosine
warmup_ratio: 0.05

# Optimization
bf16: true
gradient_checkpointing: true

# Datasets
datasets:
  - path: data/reasoning/SKGInstruct_199989.json
    type: json
  - path: data/reasoning/TableQA_distillation_39301.json
    type: json
  # ... add all datasets

# Output
output_dir: ./outputs/stage1
save_steps: 50
logging_steps: 1
```

**Step 3: Train**
```bash
accelerate launch -m axolotl.cli.train deepanalyze_stage1.yaml
```

#### ✅ Feasible: LoRA Fine-tuning
```yaml
# deepanalyze_lora.yaml

base_model: RUC-DataLab/DeepAnalyze-8B
model_type: qwen2

# LoRA
adapter: lora
lora_r: 64
lora_alpha: 128
lora_dropout: 0.05
lora_target_modules:
  - q_proj
  - k_proj
  - v_proj
  - o_proj

# Training
sequence_len: 32768
micro_batch_size: 2
gradient_accumulation_steps: 4
learning_rate: 2e-4
num_epochs: 3

# Dataset
datasets:
  - path: your_domain_data.json
    type: json
```

#### ⚠️ Uncertain: Stage 3 (RL)
**Reasons:**
- Axolotl focuses on SFT, not RL
- Would still need SkyRL or TRL
- Could use Axolotl for SFT stages, then switch to RL framework

### Performance Comparison

| Metric | ms-swift | Axolotl |
|--------|----------|---------|
| Full Fine-tuning Speed | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| LoRA Speed | ⭐⭐⭐ | ⭐⭐⭐ |
| Memory Efficiency | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Multi-GPU Support | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Sequence Packing | ✅ | ✅ |
| DeepSpeed Support | ✅ | ✅ |
| Ease of Use | ⭐⭐⭐ | ⭐⭐⭐ |
| Flexibility | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### Recommendation for Axolotl

**✅ Use Axolotl for:**
- Reproducing Stages 1-2 training
- Full fine-tuning with custom data
- Multi-GPU distributed training
- Production deployments
- When you need maximum flexibility

**❌ Don't use Axolotl for:**
- Quick LoRA experiments (use Unsloth)
- Stage 3 RL training (use SkyRL)
- When you need absolute maximum speed

---

## Comparison Matrix

| Feature | ms-swift | Unsloth | Axolotl |
|---------|----------|---------|---------|
| **Full Fine-tuning** | ✅ Excellent | ⚠️ Basic | ✅ Excellent |
| **LoRA Fine-tuning** | ✅ Good | ✅ Excellent | ✅ Good |
| **QLoRA** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Multi-GPU** | ✅ Excellent | ⚠️ Basic | ✅ Excellent |
| **DeepSpeed** | ✅ Yes | ❌ No | ✅ Yes |
| **FSDP** | ✅ Yes | ❌ No | ✅ Yes |
| **Sequence Packing** | ✅ Yes | ❌ No | ✅ Yes |
| **Flash Attention** | ✅ Yes | ✅ Yes | ✅ Yes |
| **DeepSeek-R1 Support** | ✅ Native | ⚠️ Uncertain | ⚠️ May need config |
| **Speed (LoRA)** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Speed (Full)** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Memory Efficiency** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Ease of Use** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Flexibility** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Documentation** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Community** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **RL Support** | ❌ No | ❌ No | ❌ No |

---

## Recommended Strategy

### For Different Use Cases

#### 1. Reproducing Original Training (Stages 1-2)
**Recommendation: Axolotl** ✅

**Why:**
- Full feature parity with ms-swift
- Sequence packing support
- DeepSpeed ZeRO-3 support
- Multi-GPU distributed training
- More widely used and documented

**Migration Effort:** Medium
- Need to convert configs to YAML
- May need to adjust model_type
- Test thoroughly before full training

#### 2. Domain-Specific LoRA Fine-tuning
**Recommendation: Unsloth** ✅

**Why:**
- 2-5x faster than alternatives
- 80% less memory
- Extremely easy to use
- Perfect for single-GPU setups
- Great for experimentation

**Migration Effort:** Low
- Simple Python API
- Minimal configuration
- Quick to get started

#### 3. Production Full Fine-tuning
**Recommendation: Axolotl** ✅

**Why:**
- Production-ready
- Extensive configuration options
- Strong multi-GPU support
- Active community
- Well-tested

**Migration Effort:** Medium
- YAML configuration
- Need to test thoroughly
- May need custom model configs

#### 4. Stage 3 RL Training
**Recommendation: Keep SkyRL** ✅

**Why:**
- Neither Unsloth nor Axolotl support RL
- SkyRL is specifically designed for this
- Already integrated with DeepAnalyze
- Custom environment support

**Migration Effort:** N/A
- No alternative available
- Keep existing setup

---

## Migration Roadmap

### Phase 1: Validation (1-2 weeks)

**Test with Small Dataset:**
```bash
# Test Unsloth
python test_unsloth_lora.py --data sample_1k.json

# Test Axolotl
accelerate launch -m axolotl.cli.train test_config.yaml
```

**Verify:**
- Model loads correctly
- Training runs without errors
- Loss decreases as expected
- Output format is correct
- Multi-turn capability preserved

### Phase 2: Benchmark (1 week)

**Compare Performance:**
- Training speed
- Memory usage
- Final model quality
- Multi-turn capability
- Task completion rate

**Metrics to Track:**
- Tokens/second
- GPU memory usage
- Training loss
- Validation accuracy
- Inference quality

### Phase 3: Full Migration (2-4 weeks)

**If Validation Successful:**

**For Unsloth (LoRA):**
```python
# 1. Create training script
# 2. Prepare datasets
# 3. Run training
# 4. Validate outputs
# 5. Merge LoRA weights
# 6. Test inference
```

**For Axolotl (Full):**
```yaml
# 1. Convert all configs to YAML
# 2. Test each stage separately
# 3. Run full training pipeline
# 4. Validate checkpoints
# 5. Compare with original
# 6. Deploy if successful
```

---

## Code Examples

### Unsloth LoRA Fine-tuning

```python
# unsloth_deepanalyze.py

from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import load_dataset
import torch

# Configuration
MAX_SEQ_LENGTH = 32768
MODEL_NAME = "RUC-DataLab/DeepAnalyze-8B"
OUTPUT_DIR = "deepanalyze-lora-domain"

# Load model
print("Loading model...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=None,
    load_in_4bit=False,
)

# Add LoRA adapters
print("Adding LoRA adapters...")
model = FastLanguageModel.get_peft_model(
    model,
    r=64,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_alpha=128,
    lora_dropout=0.05,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=3407,
)

# Load dataset
print("Loading dataset...")
dataset = load_dataset("json", data_files="domain_data.json", split="train")

# Format function
def format_prompts(examples):
    texts = []
    for msg in examples["messages"]:
        text = ""
        for m in msg:
            if m["role"] == "user":
                text += f"User: {m['content']}\n\n"
            elif m["role"] == "assistant":
                text += f"Assistant: {m['content']}\n\n"
        texts.append(text)
    return {"text": texts}

dataset = dataset.map(format_prompts, batched=True)

# Training arguments
training_args = TrainingArguments(
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    warmup_ratio=0.05,
    num_train_epochs=3,
    learning_rate=2e-4,
    fp16=not torch.cuda.is_bf16_supported(),
    bf16=torch.cuda.is_bf16_supported(),
    logging_steps=1,
    optim="adamw_8bit",
    weight_decay=0.01,
    lr_scheduler_type="linear",
    seed=3407,
    output_dir=OUTPUT_DIR,
    save_strategy="epoch",
    save_total_limit=3,
)

# Trainer
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LENGTH,
    args=training_args,
)

# Train
print("Starting training...")
trainer.train()

# Save
print("Saving model...")
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("Done!")
```

### Axolotl Full Fine-tuning

```yaml
# deepanalyze_axolotl.yaml

# Base model
base_model: DeepSeek-R1-0528-Qwen3-8B-AddVocab
model_type: qwen2
tokenizer_type: AutoTokenizer
trust_remote_code: true

# Sequence settings
sequence_len: 8192
sample_packing: true
pad_to_sequence_len: true
eval_sample_packing: false

# Flash Attention
flash_attention: true
flash_attention_2: true

# DeepSpeed
deepspeed: deepspeed_configs/zero3.json

# Training hyperparameters
num_epochs: 3
micro_batch_size: 8
gradient_accumulation_steps: 4
learning_rate: 5e-5
lr_scheduler: cosine
warmup_ratio: 0.05

# Optimization
bf16: true
fp16: false
tf32: true
gradient_checkpointing: true
gradient_checkpointing_kwargs:
  use_reentrant: false

# Logging and saving
logging_steps: 1
save_steps: 50
eval_steps: 50
save_total_limit: 3
output_dir: ./outputs/deepanalyze_stage1

# Datasets
datasets:
  - path: data/reasoning/SKGInstruct_199989.json
    type: json
    field: messages
  - path: data/reasoning/TableQA_distillation_39301.json
    type: json
    field: messages
  - path: data/reasoning/TableQA_refinement_39301.json
    type: json
    field: messages
  - path: data/reasoning/TableGPT_29448.json
    type: json
    field: messages
  - path: data/reasoning/file_database_3833.json
    type: json
    field: messages
  - path: data/reasoning/file_csv_3007.json
    type: json
    field: messages
  - path: data/reasoning/file_xlsx_3663.json
    type: json
    field: messages
  - path: data/reasoning/file_any_2520.json
    type: json
    field: messages
  - path: data/reasoning/math_20000.json
    type: json
    field: messages
  - path: data/reasoning/code_20000.json
    type: json
    field: messages
  - path: data/reasoning/science_20000.json
    type: json
    field: messages
  - path: data/reasoning/instruction_following_20000.json
    type: json
    field: messages
  - path: data/reasoning/other_19998.json
    type: json
    field: messages

# Chat template
chat_template: qwen2
```

**Run Training:**
```bash
accelerate launch -m axolotl.cli.train deepanalyze_axolotl.yaml
```

---

## Conclusion

### Summary

| Framework | Best For | Feasibility | Recommendation |
|-----------|----------|-------------|----------------|
| **ms-swift** | Original training | ✅ Current | Keep for reference |
| **Unsloth** | LoRA fine-tuning | ✅ High | **Use for domain adaptation** |
| **Axolotl** | Full fine-tuning | ✅ High | **Use for reproduction/custom training** |
| **SkyRL** | RL training | ✅ Required | **Keep for Stage 3** |

### Final Recommendations

1. **For Quick Domain Adaptation:**
   - **Use Unsloth** ✅
   - Fastest and easiest
   - Perfect for LoRA
   - Single GPU friendly

2. **For Reproducing Training:**
   - **Use Axolotl** ✅
   - Full feature parity
   - Better documentation
   - Wider community support

3. **For RL Training:**
   - **Keep SkyRL** ✅
   - No alternative available
   - Already integrated

4. **Hybrid Approach (Recommended):**
   - **Unsloth** for LoRA experiments
   - **Axolotl** for full fine-tuning
   - **SkyRL** for RL training
   - Best of all worlds

### Next Steps

1. **Test Unsloth** with small dataset (1-2 days)
2. **Test Axolotl** with small dataset (1-2 days)
3. **Benchmark** both against ms-swift (1 week)
4. **Choose** based on results
5. **Migrate** gradually (2-4 weeks)

**Would you like me to create:**
1. Complete migration scripts for Unsloth?
2. Complete Axolotl configs for all stages?
3. Benchmark testing plan?
4. Step-by-step migration guide?
