# DeepAnalyze Training - Quick Reference

## 🎯 3-Stage Training Pipeline

```
DeepSeek-R1-0528-Qwen3-8B (Base Model)
           ↓
    [Add Vocabulary]
           ↓
    Stage 1: Single-Ability SFT
    • 421K examples
    • 3 days, 8× A100
    • Learn individual skills
           ↓
    Stage 2: Multi-Ability Cold Start
    • 26K examples  
    • 2 days, 8× A100
    • Learn multi-turn execution
           ↓
    Stage 3: Reinforcement Learning
    • Real code execution
    • 5-7 days, 8× A100
    • Optimize autonomous behavior
           ↓
    DeepAnalyze-8B (Final Model)
```

---

## 📊 Training Data Breakdown

### Stage 1: Single-Ability (421K examples)
| Category | Examples | Purpose |
|----------|----------|---------|
| SKGInstruct | 199,989 | Structured knowledge |
| TableQA | 78,602 | Table reasoning |
| TableGPT | 29,448 | Table generation |
| File Processing | 13,023 | CSV, Excel, DB, JSON |
| Math/Code/Science | 60,000 | General capabilities |
| Instructions | 39,998 | Following instructions |

### Stage 2: Multi-Ability (26K examples)
| Category | Examples | Purpose |
|----------|----------|---------|
| Data Pipeline | 8,528 | End-to-end workflows |
| Data Analysis | 4,998 | Statistical analysis |
| Research Tasks | 12,676 | Open-ended research |

### Stage 3: RL (Rollouts)
| Category | Purpose |
|----------|---------|
| QA Tasks | Question answering |
| Data Tasks | Specific data science |
| Research | Report generation |

---

## ⚙️ Training Configuration

### Stage 1: Single-Ability
```bash
Epochs: 3
Batch Size: 8 per GPU × 8 GPUs × 4 accumulation = 256
Learning Rate: 5e-5
Max Length: 8,192 tokens
Time: ~3 days
```

### Stage 2: Multi-Ability
```bash
Epochs: 3
Batch Size: 1 per GPU × 8 GPUs × 32 accumulation = 256
Learning Rate: 5e-6 (10x lower)
Max Length: 32,768 tokens (4x longer)
Time: ~2 days
```

### Stage 3: RL
```bash
Algorithm: GRPO
Batch Size: 256
Learning Rate: 5e-7 (100x lower than Stage 1)
Rollouts: 5 per prompt
Max Turns: 30
Time: ~5-7 days
```

---

## 💰 Cost Estimate

**AWS p4d.24xlarge (8× A100 80GB):**
- $262/hour
- 10-12 days total
- **~$63,000 - $75,000**

---

## 🔧 Special Tokens Added

```python
<Analyze>    # Analysis section
</Analyze>
<Understand> # Understanding section
</Understand>
<Code>       # Code to execute
</Code>
<Execute>    # Execution results (system-injected)
</Execute>
<Answer>     # Final answer
</Answer>
```

---

## 🚀 Quick Start Training

### 1. Setup
```bash
git clone https://github.com/ruc-datalab/DeepAnalyze.git
cd DeepAnalyze
pip install -r requirements.txt
cd deepanalyze/ms-swift && pip install -e .
cd ../SkyRL && pip install -e .
```

### 2. Download Data
```bash
huggingface-cli download RUC-DataLab/DataScience-Instruct-500K
huggingface-cli download deepseek-ai/DeepSeek-R1-0528-Qwen3-8B
```

### 3. Add Vocabulary
```bash
python deepanalyze/add_vocab.py \
  --model_path DeepSeek-R1-0528-Qwen3-8B \
  --save_path DeepSeek-R1-0528-Qwen3-8B-AddVocab \
  --add_tags
```

### 4. Run Training
```bash
# Stage 1
cd deepanalyze/ms-swift
bash ../../scripts/single.sh

# Stage 2
bash ../../scripts/multi_coldstart.sh

# Stage 3
cd ../SkyRL/skyrl-train
bash ../../scripts/multi_rl.sh
```

---

## 🎓 Fine-tuning for Your Domain

### LoRA Fine-tuning (Recommended)
```bash
swift sft \
    --model "RUC-DataLab/DeepAnalyze-8B" \
    --train_type "lora" \
    --lora_rank 64 \
    --dataset "your_data.json" \
    --learning_rate 1e-4 \
    --num_train_epochs 3
```

**Benefits:**
- ✅ Only 1-2 GPUs needed
- ✅ Hours instead of days
- ✅ ~1% of parameters trained
- ✅ Easy to merge

### Data Format
```json
[
  {
    "messages": [
      {
        "role": "user",
        "content": "# Instruction\nYour task\n\n# Data\nFile 1: ..."
      },
      {
        "role": "assistant",
        "content": "<Analyze>...</Analyze>\n<Code>...</Code>"
      }
    ]
  }
]
```

---

## 🔑 Key Innovations

### 1. Curriculum Learning
Progressive difficulty builds autonomous capabilities

### 2. Structured Output
Special tokens enable reliable multi-turn interaction

### 3. Real Execution RL
Training with actual code execution teaches practical skills

### 4. Multi-Turn Optimization
Different from single-turn models - learns to iterate

---

## 📈 Training Frameworks

### ms-swift (Stages 1 & 2)
- Efficient SFT framework
- DeepSpeed ZeRO-3 support
- Flash Attention
- Sequence packing

### SkyRL (Stage 3)
- Custom RL for LLMs
- GRPO algorithm
- vLLM integration
- Real environment execution

---

## 🎯 What Each Stage Teaches

### Stage 1: Individual Skills
- ✅ Load and process files
- ✅ Write Python code
- ✅ Perform calculations
- ✅ Generate visualizations
- ❌ Can't iterate or fix errors

### Stage 2: Multi-Turn Execution
- ✅ Generate code
- ✅ Observe execution results
- ✅ Generate more code based on results
- ✅ Iterate multiple times
- ❌ Not optimized for efficiency

### Stage 3: Autonomous Optimization
- ✅ Efficient iteration
- ✅ Error recovery
- ✅ Task completion
- ✅ Minimal rounds
- ✅ High-quality outputs

---

## 📊 Performance Metrics

### After Stage 1
- Single-task accuracy: ~85%
- Multi-turn capability: ❌

### After Stage 2
- Single-task accuracy: ~83% (slight drop)
- Multi-turn capability: ✅
- Average rounds: ~8-10

### After Stage 3 (Final)
- Single-task accuracy: ~87%
- Multi-turn capability: ✅
- Average rounds: ~4-6
- Task completion: ~92%

---

## 🔬 Comparison

| Model | Single-Turn | Multi-Turn | Autonomous | Open Source |
|-------|-------------|------------|------------|-------------|
| CodeLlama | ✅ | ❌ | ❌ | ✅ |
| GPT-4 Code Interpreter | ✅ | ✅ | ⚠️ | ❌ |
| AutoGPT | ✅ | ✅ | ⚠️ | ✅ (framework) |
| **DeepAnalyze** | ✅ | ✅ | ✅ | ✅ |

---

## 💡 Tips for Fine-tuning

### 1. Start Small
- Use LoRA instead of full fine-tuning
- Start with 1K-10K examples
- Validate before scaling

### 2. Maintain Format
- Keep the structured output format
- Use the same special tokens
- Follow the prompt template

### 3. Balance Data
- Mix domain-specific with general data
- Include both single-turn and multi-turn examples
- Maintain diversity

### 4. Monitor Carefully
- Watch for catastrophic forgetting
- Check multi-turn capability
- Validate on held-out tasks

---

## 📚 Resources

- **Full Details**: `training-process.md`
- **Paper**: https://arxiv.org/abs/2510.16872
- **Model**: https://huggingface.co/RUC-DataLab/DeepAnalyze-8B
- **Data**: https://huggingface.co/datasets/RUC-DataLab/DataScience-Instruct-500K
- **Code**: https://github.com/ruc-datalab/DeepAnalyze

---

## ⏱️ Timeline Summary

```
Day 0: Setup & Data Download (4 hours)
Day 1-3: Stage 1 Training (3 days)
Day 4-5: Stage 2 Training (2 days)
Day 6-12: Stage 3 RL Training (5-7 days)
Day 13: Export & Upload (2 hours)

Total: ~12 days on 8× A100 GPUs
```

---

## 🎓 Key Takeaway

DeepAnalyze's training is a **carefully designed curriculum** that progressively builds autonomous capabilities through:

1. **Individual skills** (Stage 1)
2. **Multi-turn execution** (Stage 2)  
3. **Autonomous optimization** (Stage 3)

This approach enables the model to **iterate, observe, and adapt** - just like a human data scientist.
