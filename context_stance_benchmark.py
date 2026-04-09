import csv
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, AlbertForSequenceClassification, AlbertTokenizer

# Paths
context_checkpoint = "outputs/context_model_final"
stance_checkpoint = "checkpoints/stance/indicxnli/checkpoint-36816"
stance_tokenizer_base = "ai4bharat/indic-bert"  # Update if your stance model uses a different base
input_csv = "benchmark_claims/claim_checkability_eval_packet_v1.csv"  # 30-claim benchmark
output_csv = "benchmark_claims/context_stance_benchmark_output.csv"

# Load models and tokenizers
context_model = AutoModelForSequenceClassification.from_pretrained(context_checkpoint)
context_tokenizer = AutoTokenizer.from_pretrained(context_checkpoint)
stance_model = AlbertForSequenceClassification.from_pretrained(stance_checkpoint)
stance_tokenizer = AlbertTokenizer.from_pretrained(stance_tokenizer_base)

context_id2label = context_model.config.id2label
stance_id2label = stance_model.config.id2label

def run_context(text):
    inputs = context_tokenizer(text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        outputs = context_model(**inputs)
        pred = torch.argmax(outputs.logits, dim=1).item()
        label = context_id2label[str(pred)] if str(pred) in context_id2label else context_id2label[pred]
    return label

def run_stance(premise, hypothesis):
    inputs = stance_tokenizer(premise, hypothesis, return_tensors="pt", truncation=True)
    with torch.no_grad():
        outputs = stance_model(**inputs)
        pred = torch.argmax(outputs.logits, dim=1).item()
        label = stance_id2label[str(pred)] if str(pred) in stance_id2label else stance_id2label[pred]
    return label

results = []
with open(input_csv, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        text = row.get('text') or row.get('premise')
        hypothesis = row.get('hypothesis') or row.get('claim')
        context_label = run_context(text)
        stance_label = run_stance(text, hypothesis)
        out = dict(row)
        out['context_label'] = context_label
        out['stance_label'] = stance_label
        results.append(out)

fieldnames = list(results[0].keys())
with open(output_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in results:
        writer.writerow(row)

print(f"Wrote combined context+stance results to {output_csv}")
print(f"Processed {len(results)} rows.")
