import torch
from transformers import BertTokenizerFast, BertForSequenceClassification

MODEL_NAME = "bert-base-uncased"

print("Loading tokenizer...")
tokenizer = BertTokenizerFast.from_pretrained(MODEL_NAME)

print("Loading model...")
model = BertForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=2
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

print(f"Model loaded on {device}")
