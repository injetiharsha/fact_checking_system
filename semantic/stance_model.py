# semantic/stance_model.py

import re
from models.stance.nli_model import NLIModel


class StanceDetector:

    def __init__(self):
        self.model = NLIModel()

    def detect(self, evidence, claim):
        evidence = (evidence or "")[:800]

        # Model expects (claim, evidence)
        label, confidence = self.model.predict(claim, evidence)
        label = (label or "NEUTRAL").upper()

        stance_map = {
            "ENTAILMENT": "SUPPORT",
            "CONTRADICTION": "REFUTE",
            "NEUTRAL": "NEUTRAL",
            "LABEL_0": "REFUTE",
            "LABEL_1": "NEUTRAL",
            "LABEL_2": "SUPPORT",
            "SUPPORT": "SUPPORT",
            "REFUTE": "REFUTE",
        }

        print("\nNLI INPUT")
        print("Claim:", claim)
        print("Evidence:", evidence)
        print("Prediction:", label, confidence)

        stance = stance_map.get(label, "NEUTRAL")
        if stance != "NEUTRAL":
            return {
                "stance": stance,
                "confidence": round(confidence, 3),
            }

        # Conservative lexical fallback only for clear refutations.
        text = (evidence or "").lower()
        claim_text = (claim or "").lower()
        claim_tokens = [
            t for t in re.findall(r"[a-z0-9]+", claim_text)
            if len(t) > 2 and t not in {"the", "and", "for", "with", "from", "that"}
        ]
        overlap = sum(1 for t in claim_tokens if t in text)

        refute_cues = (
            "hoax", "fake", "myth", "false", "debunk", "does not", "doesn't",
            "cannot", "can't", "no evidence", "not true", "incorrect"
        )

        if overlap >= 2 and any(c in text for c in refute_cues):
            return {"stance": "REFUTE", "confidence": 0.62}

        return {
            "stance": "NEUTRAL",
            "confidence": round(confidence, 3),
        }
