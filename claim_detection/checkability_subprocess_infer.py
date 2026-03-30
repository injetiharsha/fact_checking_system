import argparse
import json
import re

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer


LABEL_TO_SUBTYPE = {
    "factual_claim": "factual_claim",
    "personal_statement": "personal_statement",
    "opinion": "opinion",
    "question_or_rewrite": "question_or_rewrite",
    "other_uncheckable": "other_uncheckable",
    "empty": "other_uncheckable",
}

SUBTYPE_TO_GATE = {
    "factual_claim": "checkable",
    "personal_statement": "uncheckable",
    "opinion": "uncheckable",
    "question_or_rewrite": "uncheckable",
    "other_uncheckable": "uncheckable",
}


def main():
    parser = argparse.ArgumentParser(description="Isolated claim checkability inference helper.")
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
        max_length=256,
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=1)

    predicted = torch.argmax(probs, dim=1).item()
    raw_label = str(model.config.id2label.get(predicted, f"LABEL_{predicted}")).lower()
    subtype = LABEL_TO_SUBTYPE.get(raw_label, "other_uncheckable")
    label = SUBTYPE_TO_GATE.get(subtype, "uncheckable")
    confidence = probs[0][predicted].item()
    scores = {
        str(model.config.id2label.get(idx, idx)).lower(): float(probs[0][idx].item())
        for idx in range(probs.shape[-1])
    }

    print(
        json.dumps(
            {
                "label": label,
                "subtype": subtype,
                "confidence": float(confidence),
                "scores": scores,
            }
        )
    )


if __name__ == "__main__":
    main()
