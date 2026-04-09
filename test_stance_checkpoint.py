import torch
from transformers import AlbertForSequenceClassification, AlbertTokenizer

# Path to the checkpoint directory
checkpoint_dir = r"F:/fact_checking_system/checkpoints/stance/indicxnli/checkpoint-36816"

# Load model and tokenizer
model = AlbertForSequenceClassification.from_pretrained(checkpoint_dir)
tokenizer = AlbertTokenizer.from_pretrained(checkpoint_dir)

# Example input (replace with your own premise and hypothesis)
premise = "The sky is blue."
hypothesis = "The sky is colored."

# Tokenize input for NLI (Natural Language Inference)
inputs = tokenizer(premise, hypothesis, return_tensors="pt", truncation=True, padding=True)

# Run inference
with torch.no_grad():
    outputs = model(**inputs)
    logits = outputs.logits
    predicted_class_id = logits.argmax(dim=-1).item()

# Map class id to label (use int key)
id2label = model.config.id2label
if isinstance(id2label, dict):
    # Try int key first, fallback to string key
    try:
        predicted_label = id2label[predicted_class_id]
    except KeyError:
        predicted_label = id2label[str(predicted_class_id)]
else:
    predicted_label = id2label[predicted_class_id]

print(f"Prediction: {predicted_label}")
