import csv
from transformers import AlbertForSequenceClassification, AlbertTokenizer
import torch


# Path to checkpoint directory
checkpoint_dir = "checkpoints/stance/indicxnli/checkpoint-36816"
# Use the base model name for tokenizer (update if needed)
base_model_name = "ai4bharat/indic-bert"  # Change to your ALBERT base if different


# Load model and tokenizer
model = AlbertForSequenceClassification.from_pretrained(checkpoint_dir)
tokenizer = AlbertTokenizer.from_pretrained(base_model_name)


# Get id2label mapping
id2label = model.config.id2label

# Read input CSV (premise, hypothesis)
input_csv = "stance_batch_input.csv"  # Place your CSV here
output_csv = "stance_batch_output.csv"

results = []

with open(input_csv, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        premise = row['premise']
        hypothesis = row['hypothesis']
        inputs = tokenizer(premise, hypothesis, return_tensors="pt", truncation=True)
        with torch.no_grad():
            outputs = model(**inputs)
            pred = torch.argmax(outputs.logits, dim=1).item()
            label = id2label[str(pred)] if str(pred) in id2label else id2label[pred]
        results.append({
            'premise': premise,
            'hypothesis': hypothesis,
            'prediction': label
        })

# Write results to output CSV
with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['premise', 'hypothesis', 'prediction']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in results:
        writer.writerow(row)

print(f"Batch predictions written to {output_csv}")
print(f"Processed {len(results)} rows.")
