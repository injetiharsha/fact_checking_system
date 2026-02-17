# claim_detection/classifier.py

from models.claim_classifier.model import ClaimClassifierModel


class ClaimClassifier:

    def __init__(self):
        self.model = ClaimClassifierModel()

    def classify(self, text):
        return self.model.predict(text)
