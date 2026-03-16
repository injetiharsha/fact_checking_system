import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

from claim_detection.context_taxonomy import CONTEXT_TAXONOMY, INDIA_STATE_ALIASES
from training.common.config import runtime_model_settings


DOMAIN_HINTS: Dict[str, Dict[str, List[str]]] = {
    "science": {
        "physics": ["lightning", "freeze", "surface of the sun", "sound", "dna"],
        "biology": ["banana", "berries", "berries", "octopus", "sharks", "bats", "mammals"],
        "earth_science": ["earth", "flat", "round", "continents", "river", "lake"],
        "scientific_consensus": ["consensus", "evidence", "scientists", "researchers"],
    },
    "health": {
        "public_health": ["covid", "pandemic", "virus", "disease"],
        "toxicology": ["bleach", "toxic", "poison"],
        "nutrition": ["diet", "nutrition"],
        "disease_treatment": ["cures", "treatment", "vaccine", "medicine", "drug"],
    },
    "technology": {
        "telecom": ["5g", "network", "telecom"],
        "software_ai": ["ai", "software", "algorithm", "dataset", "images", "scans", "augmented reality", "ar app", "spatial"],
        "social_media": ["twitter", "facebook", "instagram", "youtube"],
    },
    "history": {
        "wars_conflicts": ["world war", "war ii", "conflict", "empire"],
        "historical_events": ["fell in", "invented", "founded", "ended in", "berlin wall", "printing press"],
        "historical_figures": ["gutenberg", "roosevelt"],
    },
    "politics_government": {
        "foreign_affairs": ["minister", "lok sabha", "parliament", "government", "opposition", "diplomat"],
        "elections": ["election", "vote", "voter"],
        "public_policy": ["policy", "scheme", "bill", "act", "school policy", "education policy", "government announced"],
    },
    "economics_business": {
        "macroeconomics": ["inflation", "gdp", "economy", "unemployment"],
        "finance": ["bank", "reserve bank", "interest rate", "rupee"],
        "markets": ["stock", "market", "shares"],
    },
    "geography": {
        "countries": ["country", "capital", "island"],
        "continents": ["continent", "africa", "australia", "greenland"],
        "rivers_lakes": ["river", "lake", "baikal", "amazon"],
    },
    "space_astronomy": {
        "planets": ["mars", "venus", "jupiter", "saturn", "neptune"],
        "moons": ["moon", "moons"],
        "stars": ["sun", "star"],
        "space_missions": ["moon landing", "apollo", "nasa", "space"],
    },
    "environment_climate": {
        "climate_change": ["climate change", "global warming", "emissions"],
        "disasters_weather": ["cyclone", "earthquake", "flood", "storm"],
        "biodiversity": ["extinct", "species"],
    },
    "society_culture": {
        "education": ["university", "school", "education"],
        "demographics": ["population", "census"],
        "language_identity": ["language", "culture", "tradition"],
    },
    "law_crime": {
        "courts": ["court", "judge", "supreme court", "high court"],
        "regulation": ["law", "legal", "illegal", "regulation"],
        "criminal_cases": ["crime", "arrest", "charged"],
    },
    "sports": {
        "teams": ["team", "club"],
        "athletes": ["player", "athlete"],
        "tournaments": ["world cup", "ipl", "olympics", "tournament", "match"],
        "records": ["record", "champion"],
    },
    "entertainment": {
        "film": ["movie", "film", "cinema"],
        "television": ["tv", "series", "show"],
        "music": ["song", "album", "music"],
        "celebrity": ["actor", "actress", "celebrity"],
        "gaming": ["game", "gaming"],
    },
}

DOMAIN_TO_DEFAULT_SUBCATEGORY = {
    "science": "scientific_consensus",
    "health": "public_health",
    "technology": "software_ai",
    "history": "historical_events",
    "politics_government": "public_policy",
    "economics_business": "macroeconomics",
    "geography": "countries",
    "space_astronomy": "space_missions",
    "environment_climate": "climate_change",
    "society_culture": "demographics",
    "law_crime": "courts",
    "sports": "tournaments",
    "entertainment": "film",
    "general_factual": "encyclopedic",
}


class ClaimContextClassifier:
    """Context classifier with trained-model-first support and lexical fallback."""

    MODEL_CONFIDENCE_THRESHOLD = 0.55

    def __init__(self):
        self.trained_checkpoint = None
        self.trained_device = "cpu"
        self.helper_script = Path(__file__).with_name("context_subprocess_infer.py")

        runtime = runtime_model_settings("context")
        checkpoint = runtime.get("checkpoint")
        if runtime.get("enabled") and checkpoint is not None:
            self.trained_checkpoint = Path(checkpoint)
            self.trained_device = runtime.get("device") or "cpu"
            print(
                "ClaimContextClassifier using trained checkpoint via isolated inference:",
                checkpoint,
            )

    def classify(self, claim: str) -> dict:
        if self.trained_checkpoint is not None:
            trained_result = self._classify_with_subprocess(claim)
            if trained_result is not None:
                return trained_result
        return self._heuristic_classify(claim)

    def _heuristic_classify(self, claim: str) -> dict:
        claim_text = " ".join((claim or "").strip().lower().split())
        domain = "general_factual"
        subcategory = "encyclopedic"
        confidence = 0.3
        decision_source = "fallback_general"

        best_score = 0
        for domain_name, subcategories in DOMAIN_HINTS.items():
            for subcategory_name, hints in subcategories.items():
                score = sum(1 for hint in hints if hint in claim_text)
                if score > best_score:
                    best_score = score
                    domain = domain_name
                    subcategory = subcategory_name

        if best_score > 0:
            confidence = min(0.45 + (best_score * 0.12), 0.82)
            decision_source = "bootstrap_lexical_context"

        state_focus = self._detect_state_focus(claim_text)
        risk_flags = self._detect_risk_flags(claim_text, state_focus)

        if state_focus:
            confidence = max(confidence, 0.62)

        result = {
            "domain": domain,
            "subcategory": subcategory,
            "confidence": round(float(confidence), 3),
            "decision_source": decision_source,
            "risk_flags": risk_flags,
            "state_focus": state_focus,
            "taxonomy_version": "v1",
            "available_domains": list(CONTEXT_TAXONOMY.keys()),
        }
        return result

    def _best_subcategory_for_domain(self, claim_text: str, domain: str) -> str:
        subcategories = DOMAIN_HINTS.get(domain, {})
        best_subcategory = DOMAIN_TO_DEFAULT_SUBCATEGORY.get(domain, "encyclopedic")
        best_score = 0
        for subcategory_name, hints in subcategories.items():
            score = sum(1 for hint in hints if hint in claim_text)
            if score > best_score:
                best_score = score
                best_subcategory = subcategory_name
        return best_subcategory

    def _classify_with_subprocess(self, claim: str):
        if not self.helper_script.exists():
            return None

        command = [
            sys.executable,
            str(self.helper_script),
            "--checkpoint",
            str(self.trained_checkpoint),
            "--device",
            self.trained_device,
            "--text",
            claim,
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=45,
                check=False,
            )
        except Exception as exc:
            print(f"Trained context subprocess failed to start: {exc}")
            return None

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            if stderr:
                print(f"Trained context subprocess failed: {stderr[:300]}")
            return None

        stdout = (completed.stdout or "").strip().splitlines()
        if not stdout:
            return None

        try:
            payload = json.loads(stdout[-1])
        except Exception as exc:
            print(f"Invalid trained context subprocess output: {exc}")
            return None

        label = str(payload.get("label") or "general_factual").lower()
        confidence = float(payload.get("confidence") or 0.0)
        if confidence < self.MODEL_CONFIDENCE_THRESHOLD:
            fallback = self._heuristic_classify(claim)
            fallback["decision_source"] = "bootstrap_lexical_low_trained_context_confidence"
            fallback["model_domain"] = label
            fallback["model_confidence"] = round(confidence, 3)
            fallback["scores"] = payload.get("scores", {})
            return fallback

        claim_text = " ".join((claim or "").strip().lower().split())
        state_focus = self._detect_state_focus(claim_text)
        risk_flags = self._detect_risk_flags(claim_text, state_focus)
        result = {
            "domain": label,
            "subcategory": self._best_subcategory_for_domain(claim_text, label),
            "confidence": round(confidence, 3),
            "decision_source": "trained_context_model",
            "risk_flags": risk_flags,
            "state_focus": state_focus,
            "taxonomy_version": "v1",
            "available_domains": list(CONTEXT_TAXONOMY.keys()),
            "scores": payload.get("scores", {}),
        }
        return result

    def _detect_state_focus(self, claim_text: str) -> str | None:
        for state_name, aliases in INDIA_STATE_ALIASES.items():
            for alias in aliases:
                pattern = r"\b" + re.escape(alias.lower()) + r"\b"
                if re.search(pattern, claim_text):
                    return state_name
        return None

    @staticmethod
    def _detect_risk_flags(claim_text: str, state_focus: str | None) -> list[str]:
        flags = []
        if state_focus:
            flags.append("regional_local_claim")
        return flags



