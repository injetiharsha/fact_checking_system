import torch
from app.ml.model_loader import tokenizer, model, device

LABELS = {
    0: "FAKE",
    1: "REAL"
}

def run_inference(text: str):
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=256
    )

    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1)

    confidence, prediction = torch.max(probs, dim=1)

    return {
        "label": LABELS[prediction.item()],
        "confidence": round(confidence.item(), 4)
    }
