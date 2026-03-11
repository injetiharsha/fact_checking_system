import argparse
import json

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def main():
    parser = argparse.ArgumentParser(description="Isolated stance inference helper.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--claim", required=True)
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()

    device = torch.device(args.device)
    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint, use_fast=False)
    model = AutoModelForSequenceClassification.from_pretrained(args.checkpoint).to(device)
    model.eval()

    inputs = tokenizer(
        args.claim,
        args.evidence,
        return_tensors="pt",
        truncation=True,
        padding=True,
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=1)

    predicted = torch.argmax(probs, dim=1).item()
    confidence = probs[0][predicted].item()
    label = model.config.id2label.get(predicted, f"LABEL_{predicted}")

    print(json.dumps({
        "label": label,
        "confidence": float(confidence),
    }))


if __name__ == "__main__":
    main()
