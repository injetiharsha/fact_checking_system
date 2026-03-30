import argparse
import json

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def main():
    parser = argparse.ArgumentParser(description="Isolated claim type inference helper.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--text", required=True)
    args = parser.parse_args()

    device = torch.device(args.device)
    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint, use_fast=False)
    model = AutoModelForSequenceClassification.from_pretrained(args.checkpoint).to(device)
    model.eval()

    inputs = tokenizer(
        args.text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=1)

    predicted = torch.argmax(probs, dim=1).item()
    label = model.config.id2label.get(predicted, f"LABEL_{predicted}")
    confidence = probs[0][predicted].item()
    scores = {
        str(model.config.id2label.get(idx, idx)).lower(): float(probs[0][idx].item())
        for idx in range(probs.shape[-1])
    }

    print(
        json.dumps(
            {
                "label": str(label).lower(),
                "confidence": float(confidence),
                "scores": scores,
            }
        )
    )


if __name__ == "__main__":
    main()
