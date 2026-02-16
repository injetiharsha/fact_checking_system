# semantic/stance_model.py

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F

class StanceDetector:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.tokenizer = AutoTokenizer.from_pretrained(
            "ynie/roberta-large-snli_mnli_fever_anli_R1_R2_R3-nli"
        )

        self.model = AutoModelForSequenceClassification.from_pretrained(
            "ynie/roberta-large-snli_mnli_fever_anli_R1_R2_R3-nli"
        ).to(self.device)

        self.labels = ["CONTRADICTION", "NEUTRAL", "ENTAILMENT"]

    def detect(self, claim, evidence):
        inputs = self.tokenizer(
            claim,
            evidence,
            return_tensors="pt",
            truncation=True,
            padding=True
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = F.softmax(outputs.logits, dim=1)

        predicted = torch.argmax(probs, dim=1).item()
        confidence = probs[0][predicted].item()

        stance_map = {
            "ENTAILMENT": "SUPPORT",
            "CONTRADICTION": "REFUTE",
            "NEUTRAL": "NEUTRAL"
        }

        return {
            "stance": stance_map[self.labels[predicted]],
            "confidence": round(confidence, 3)
        }
