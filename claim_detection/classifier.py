# claim_detection/classifier.py

from transformers import pipeline
import torch

class ClaimClassifier:
    def __init__(self):
        self.classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=0 if torch.cuda.is_available() else -1
        )
        self.labels = ["factual claim", "opinion", "prediction", "emotional statement"]

    def classify(self, text):
        result = self.classifier(text, self.labels)
        return result
