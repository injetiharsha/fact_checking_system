# semantic/stance_model.py

from models.stance.nli_model import NLIModel


class StanceDetector:

    def __init__(self):
        self.model = NLIModel()

    def detect(self, evidence, claim):
        evidence = evidence[:800]

        label, confidence = self.model.predict(evidence, claim)

        label = label.upper()

        stance_map = {
            "ENTAILMENT": "SUPPORT",
            "CONTRADICTION": "REFUTE",
            "NEUTRAL": "NEUTRAL",
            "LABEL_0": "REFUTE",
            "LABEL_1": "NEUTRAL",
            "LABEL_2": "SUPPORT",
            "SUPPORT": "SUPPORT",
            "REFUTE": "REFUTE"
        }

        stance = stance_map.get(label, "NEUTRAL")

        print("\nNLI INPUT")
        print("Claim:", claim)
        print("Evidence:", evidence)
        print("Prediction:", label, confidence)

        # Simple negation override
        text = evidence.lower()
        claim_text = claim.lower()

        if "not" in text or "isn't" in text or "no" in text:
            if any(word in text for word in claim_text.split()):
                return {
                    "stance": "REFUTE",
                    "confidence": 0.9
                }

        return {
            "stance": stance_map.get(label, label),
            "confidence": round(confidence, 3)
        }

    