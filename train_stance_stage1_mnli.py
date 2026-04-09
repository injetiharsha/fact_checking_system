
import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from datasets import load_dataset, DatasetDict, Dataset
import numpy as np
from collections import Counter

# Print CUDA status
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("CUDA device count:", torch.cuda.device_count())
    print("CUDA device name:", torch.cuda.get_device_name(0))
else:
    print("Running on CPU. No CUDA device detected.")

# Set data directory
DATA_DIR = "./data_multinli"
os.makedirs(DATA_DIR, exist_ok=True)

# Download and cache MultiNLI dataset locally if not already present
if not (os.path.exists(os.path.join(DATA_DIR, "multi_nli-train.arrow")) and os.path.exists(os.path.join(DATA_DIR, "multi_nli-validation_matched.arrow"))):
    print("Downloading Multi-Genre NLI dataset to local cache...")
    dataset = load_dataset("multi_nli")
    dataset["train"].save_to_disk(os.path.join(DATA_DIR, "multi_nli-train"))
    dataset["validation_matched"].save_to_disk(os.path.join(DATA_DIR, "multi_nli-validation_matched"))
else:
    print("Loading Multi-Genre NLI dataset from local cache...")
    from datasets import load_from_disk
    train_data = load_from_disk(os.path.join(DATA_DIR, "multi_nli-train"))
    val_data = load_from_disk(os.path.join(DATA_DIR, "multi_nli-validation_matched"))
    dataset = DatasetDict({"train": train_data, "validation_matched": val_data})


# Create train/val/test split from original train set
from datasets import load_dataset
raw_dataset = load_dataset("multi_nli")
split_dataset = raw_dataset["train"].train_test_split(test_size=0.1, seed=42)
train_split = split_dataset["train"]
test_split = split_dataset["test"]
val_split = raw_dataset["validation_matched"]

# Load tokenizer and model
model_name = "ai4bharat/indic-bert"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=3)

def preprocess_and_tokenize(batch):
    tokenized = tokenizer(batch["premise"], batch["hypothesis"], truncation=True, padding="max_length", max_length=128)
    tokenized["label"] = batch["label"]
    return tokenized

train_data = train_split.map(preprocess_and_tokenize, batched=True)
val_data = val_split.map(preprocess_and_tokenize, batched=True)
test_data = test_split.map(preprocess_and_tokenize, batched=True)

print("Label distribution before filtering (train):", Counter(train_data["label"]))
print("Label distribution before filtering (val):", Counter(val_data["label"]))
print("Label distribution before filtering (test):", Counter(test_data["label"]))

# Filter out samples with label == -1 (if any)
train_data = train_data.filter(lambda x: x["label"] != -1)
val_data = val_data.filter(lambda x: x["label"] != -1)
test_data = test_data.filter(lambda x: x["label"] != -1)

print("Number of training samples after filtering:", len(train_data))
print("Number of validation samples after filtering:", len(val_data))
print("Number of test samples after filtering:", len(test_data))

# After filtering, keep only input_ids, attention_mask, and label
train_data = train_data.remove_columns([col for col in train_data.column_names if col not in ["input_ids", "attention_mask", "label"]])
val_data = val_data.remove_columns([col for col in val_data.column_names if col not in ["input_ids", "attention_mask", "label"]])
test_data = test_data.remove_columns([col for col in test_data.column_names if col not in ["input_ids", "attention_mask", "label"]])

print("Train columns after removing extra:", train_data.column_names)
print("Val columns after removing extra:", val_data.column_names)
print("Test columns after removing extra:", test_data.column_names)

train_data.set_format(type="torch", columns=["input_ids", "attention_mask", "label"])
val_data.set_format(type="torch", columns=["input_ids", "attention_mask", "label"])
test_data.set_format(type="torch", columns=["input_ids", "attention_mask", "label"])

training_args = TrainingArguments(
    output_dir="./results_mnli",
    num_train_epochs=3,  # Increased epochs for better training
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    logging_steps=100,
    report_to=["none"],
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    fp16=torch.cuda.is_available(),
    disable_tqdm=False,
)


from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    acc = accuracy_score(labels, preds)
    precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average="weighted", zero_division=0)
    cm = confusion_matrix(labels, preds)
    return {
        "accuracy": acc,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "confusion_matrix": cm.tolist(),
    }


trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_data,
    eval_dataset=val_data,
    compute_metrics=compute_metrics,
)

print("Starting training...")
trainer.train()
print("Training complete. Best model saved in ./results_mnli/")

# Evaluate on test set

print("Evaluating on test set...")
test_results = trainer.evaluate(test_data)
print("Test set results:", test_results)
# Save test results to file
import json
with open("./results_mnli/test_results.json", "w") as f:
    json.dump(test_results, f, indent=2)
print("Test results saved to ./results_mnli/test_results.json")
