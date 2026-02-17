import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch.nn.functional as F

class NLIModel:

    def __init__(self):

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        print("Using device:", self.device)

        self.tokenizer = AutoTokenizer.from_pretrained(
            "ynie/roberta-large-snli_mnli_fever_anli_R1_R2_R3-nli"
        )

        self.model = AutoModelForSequenceClassification.from_pretrained(
            "ynie/roberta-large-snli_mnli_fever_anli_R1_R2_R3-nli"
        ).to(self.device)

        self.labels = ["CONTRADICTION", "NEUTRAL", "ENTAILMENT"]

    def predict(self, claim, evidence):

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

        return self.labels[predicted], confidence
