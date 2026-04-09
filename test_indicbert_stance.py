

import torch
from transformers import AutoModel, AutoTokenizer

# Load model and tokenizer for IndicBERT (embedding/feature extraction only)
model_name = "ai4bharat/indic-bert"
model = AutoModel.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

print("IndicBERT model loaded successfully. You can now use it for embedding extraction or downstream tasks.")

# Example test samples (Hindi, English, and code-mixed)
test_samples = [
    {"claim": "भारत में सबसे ऊँचा पर्वत हिमालय है।", "evidence": "हिमालय भारत का सबसे ऊँचा पर्वत है।", "label": "SUPPORT"},
    {"claim": "The Taj Mahal is in Mumbai.", "evidence": "The Taj Mahal is located in Agra.", "label": "REFUTE"},
    {"claim": "ಚೆನ್ನೈ ಭಾರತದ ರಾಜಧಾನಿ ಆಗಿದೆ.", "evidence": "ನವದೆಹಲಿ ಭಾರತದ ರಾಜಧಾನಿ.", "label": "REFUTE"},
    {"claim": "Kerala is known for its backwaters.", "evidence": "Kerala has a famous network of backwaters.", "label": "SUPPORT"},
]

# Prepare inputs for NLI-style classification (premise: evidence, hypothesis: claim)
def predict_stance(claim, evidence):
    inputs = tokenizer(evidence, claim, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
        if hasattr(outputs, 'logits'):
            probs = torch.softmax(outputs.logits, dim=-1).squeeze().tolist()
            return probs
        else:
            return None

print("\nIndicBERT Stance Baseline Results:")
for sample in test_samples:
    probs = predict_stance(sample["claim"], sample["evidence"])
    print(f"Claim: {sample['claim']}")
    print(f"Evidence: {sample['evidence']}")
    print(f"True Label: {sample['label']}")
    if probs:
        print(f"Model Output (probabilities): {probs}")
    else:
        print("Model does not have a classification head.")
    print("-"*40)
