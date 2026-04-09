import csv
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from sklearn.metrics import accuracy_score, classification_report

# Paths
checkpoint_dir = "outputs/context_model_final"
test_csv = "outputs/test.csv"

# Load model and tokenizer
model = AutoModelForSequenceClassification.from_pretrained(checkpoint_dir)
tokenizer = AutoTokenizer.from_pretrained(checkpoint_dir)
model.eval()

# Read test data
texts = []
labels = []
with open(test_csv, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        texts.append(row['text'])
        labels.append(row['label'].upper())

# Get label mapping
id2label = model.config.id2label
label2id = {v.upper(): int(k) for k, v in id2label.items()}

# Predict
preds = []
for text in texts:
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
        pred = torch.argmax(outputs.logits, dim=1).item()
        preds.append(pred)

# Convert gold labels to ids
label_ids = [label2id.get(l, -1) for l in labels]

# Filter out any unknown labels
valid = [i for i, lid in enumerate(label_ids) if lid != -1]
label_ids = [label_ids[i] for i in valid]
preds = [preds[i] for i in valid]

# Accuracy and report
acc = accuracy_score(label_ids, preds)
print(f"Context model accuracy: {acc:.2%} ({sum([p==l for p,l in zip(preds,label_ids)])}/{len(label_ids)})")
print(classification_report(label_ids, preds, target_names=[id2label[str(i)] for i in range(len(id2label))]))
