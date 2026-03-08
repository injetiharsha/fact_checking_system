# semantic/stance_model.py

from models.stance.nli_model import NLIModel
import re


class StanceDetector:

    def __init__(self):
        self.model = NLIModel()

    def detect(self, evidence, claim):
        evidence = evidence[:800]

        # Correct order: model expects (claim, evidence).
        label, confidence = self.model.predict(claim, evidence)

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

        stance = stance_map.get(label, "NEUTRAL")
        if stance != "NEUTRAL":
            return {
                "stance": stance,
                "confidence": round(confidence, 3)
            }

        # Neutral fallback: use light lexical cues.
        text = (evidence or "").lower()
        claim_text = (claim or "").lower()
        claim_tokens = [
            t for t in re.findall(r"[a-z0-9]+", claim_text)
            if len(t) > 2 and t not in {"the", "and", "for", "with", "from", "that"}
        ]
        overlap = sum(1 for t in claim_tokens if t in text)

        refute_cues = (
            "hoax", "fake", "myth", "false", "debunk", "does not", "doesn't",
            "cannot", "can't", "no evidence"
        )
        support_cues = (
            "is true", "confirmed", "proven", "fact check true", "evidence shows"
        )

        if overlap >= 2 and any(c in text for c in refute_cues):
            return {"stance": "REFUTE", "confidence": 0.62}
        if claim_text in text or (overlap >= 3 and any(c in text for c in support_cues)):
            return {"stance": "SUPPORT", "confidence": 0.6}

        return {
            "stance": "NEUTRAL",
            "confidence": round(confidence, 3)
        }

    
