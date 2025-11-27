#!/usr/bin/env python3
"""
Unsloth LoRA Fine-tuning for DeepAnalyze
Adds Azure Blob Storage and PostgreSQL capabilities
"""

from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import load_dataset
import torch
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="RUC-DataLab/DeepAnalyze-8B")
    parser.add_argument("--data", required=True, help="Path to training data JSON")
    parser.add_argument("--output", default="deepanalyze-cloud-lora")
    parser.add_argument("--max_seq_length", type=int, default=32768)
    parser.add_argument("--lora_rank", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--learning_rate", type=float, default=2e-4)
    args = parser.parse_args()

    print(f"🚀 Loading model: {args.model}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model,
        max_seq_length=args.max_seq_length,
        dtype=None,
        load_in_4bit=False,
    )

    print(f"🔧 Adding LoRA adapters (rank={args.lora_rank})")
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_rank,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_alpha=args.lora_rank * 2,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    print(f"📚 Loading dataset: {args.data}")
    dataset = load_dataset("json", data_files=args.data, split="train")

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

    print(f"🎯 Training configuration:")
    print(f"   - Epochs: {args.epochs}")
    print(f"   - Batch size: {args.batch_size}")
    print(f"   - Learning rate: {args.learning_rate}")
    print(f"   - Max sequence length: {args.max_seq_length}")

    training_args = TrainingArguments(
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        warmup_ratio=0.05,
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=1,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        output_dir=args.output,
        save_strategy="epoch",
        save_total_limit=3,
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=args.max_seq_length,
        args=training_args,
    )

    print("🏋️ Starting training...")
    trainer.train()

    print(f"💾 Saving model to: {args.output}")
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)

    print("✅ Training complete!")

if __name__ == "__main__":
    main()
