# semantic/stance_model.py

from models.stance.nli_model import NLIModel


class StanceDetector:

    def __init__(self):
        self.model = NLIModel()

    def detect(self, claim, evidence):

        label, confidence = self.model.predict(claim, evidence)

        stance_map = {
            "ENTAILMENT": "SUPPORT",
            "CONTRADICTION": "REFUTE",
            "NEUTRAL": "NEUTRAL"
        }

        return {
            "stance": stance_map[label],
            "confidence": round(confidence, 3)
        }
