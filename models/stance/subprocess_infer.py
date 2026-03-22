import argparse
import json

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def predict_pair(model, tokenizer, device, claim, evidence):
    inputs = tokenizer(
        claim,
        evidence,
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
    return {"label": label, "confidence": float(confidence)}


def predict_pairs(model, tokenizer, device, rows):
    if not rows:
        return []

    claims = [row.get("claim", "") for row in rows]
    evidences = [row.get("evidence", "") for row in rows]
    inputs = tokenizer(
        claims,
        evidences,
        return_tensors="pt",
        truncation=True,
        padding=True,
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=1)

    predicted = torch.argmax(probs, dim=1).tolist()
    confidences = probs.max(dim=1).values.tolist()
    labels = [model.config.id2label.get(idx, f"LABEL_{idx}") for idx in predicted]
    return [
        {"label": label, "confidence": float(conf)}
        for label, conf in zip(labels, confidences)
    ]


def main():
    parser = argparse.ArgumentParser(description="Isolated stance inference helper.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--claim", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()

    device = torch.device(args.device)
    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint, use_fast=False)
    model = AutoModelForSequenceClassification.from_pretrained(args.checkpoint).to(device)
    model.eval()

    if args.serve:
        print(json.dumps({"status": "ready"}), flush=True)
        while True:
            try:
                line = input()
            except EOFError:
                break
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except Exception as exc:
                print(json.dumps({"error": f"invalid_json:{exc}"}), flush=True)
                continue

            if payload.get("command") == "shutdown":
                print(json.dumps({"status": "bye"}), flush=True)
                break

            if isinstance(payload.get("items"), list):
                print(json.dumps({"predictions": predict_pairs(model, tokenizer, device, payload["items"])}), flush=True)
                continue

            result = predict_pair(model, tokenizer, device, payload.get("claim", ""), payload.get("evidence", ""))
            print(json.dumps(result), flush=True)
        return

    result = predict_pair(model, tokenizer, device, args.claim, args.evidence)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
