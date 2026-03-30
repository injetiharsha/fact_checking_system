import argparse
import json

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def score_pair(model, tokenizer, device, claim, text):
    inputs = tokenizer(
        claim,
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=256,
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits

    if logits.shape[-1] == 1:
        score = torch.sigmoid(logits[0][0]).item()
    else:
        score = F.softmax(logits, dim=-1)[0][-1].item()
    return float(score)


def score_pairs(model, tokenizer, device, rows):
    if not rows:
        return []

    claims = [row.get("claim", "") for row in rows]
    texts = [row.get("text", "") for row in rows]
    inputs = tokenizer(
        claims,
        texts,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=256,
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits

    if logits.shape[-1] == 1:
        scores = torch.sigmoid(logits[:, 0]).tolist()
    else:
        scores = F.softmax(logits, dim=-1)[:, -1].tolist()
    return [float(score) for score in scores]


def main():
    parser = argparse.ArgumentParser(description="Isolated relevance inference helper.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--claim", required=True)
    parser.add_argument("--text", required=True)
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
                scores = score_pairs(model, tokenizer, device, payload["items"])
                print(json.dumps({"scores": scores}), flush=True)
                continue

            claim = payload.get("claim", "")
            text = payload.get("text", "")
            score = score_pair(model, tokenizer, device, claim, text)
            print(json.dumps({"score": score}), flush=True)
        return

    score = score_pair(model, tokenizer, device, args.claim, args.text)
    print(json.dumps({"score": score}))


if __name__ == "__main__":
    main()
