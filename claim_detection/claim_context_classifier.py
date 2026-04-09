import json
import os
import torch
import re
import subprocess
import sys
import threading
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


LANGUAGE_LOCALITY_HINTS: Dict[str, Dict[str, List[str] | str]] = {
    "te": {
        "countries": ["india"],
        "states": ["andhra_pradesh", "telangana"],
        "query_language": "telugu",
    },
    "ta": {
        "countries": ["india", "sri_lanka"],
        "states": ["tamil_nadu"],
        "query_language": "tamil",
    },
    "kn": {
        "countries": ["india"],
        "states": ["karnataka"],
        "query_language": "kannada",
    },
    "ml": {
        "countries": ["india"],
        "states": ["kerala"],
        "query_language": "malayalam",
    },
    "bn": {
        "countries": ["india", "bangladesh"],
        "states": ["west_bengal"],
        "query_language": "bengali",
    },
    "mr": {
        "countries": ["india"],
        "states": ["maharashtra"],
        "query_language": "marathi",
    },
    "gu": {
        "countries": ["india"],
        "states": ["gujarat"],
        "query_language": "gujarati",
    },
    "pa": {
        "countries": ["india", "pakistan"],
        "states": ["punjab"],
        "query_language": "punjabi",
    },
    "or": {
        "countries": ["india"],
        "states": ["odisha"],
        "query_language": "odia",
    },
    "hi": {
        "countries": ["india"],
        "states": ["uttar_pradesh", "bihar", "rajasthan", "delhi", "madhya_pradesh"],
        "query_language": "hindi",
    },
}


class ClaimContextClassifier:
    """Context classifier with trained-model-first support and lexical fallback."""

    MODEL_CONFIDENCE_THRESHOLD = 0.55

    def __init__(self):
        self.trained_checkpoint = None
        self.trained_device = os.getenv("CONTEXT_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
        self.helper_script = Path(__file__).with_name("context_subprocess_infer.py")
        self._worker = None
        self._worker_lock = threading.Lock()
        self._worker_ready = False

        runtime = runtime_model_settings("context")
        checkpoint = runtime.get("checkpoint")
        if runtime.get("enabled") and checkpoint is not None:
            self.trained_checkpoint = Path(checkpoint)
            self.trained_device = runtime.get("device") or ("cuda" if torch.cuda.is_available() else "cpu")

    def _start_worker(self) -> bool:
        if self._worker_ready and self._worker is not None and self._worker.poll() is None:
            return True
        if self.trained_checkpoint is None or not self.helper_script.exists():
            return False

        command = [
            sys.executable,
            str(self.helper_script),
            "--checkpoint",
            str(self.trained_checkpoint),
            "--device",
            self.trained_device,
            "--serve",
        ]

        try:
            self._worker = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
        except Exception as exc:
            print(f"Failed to start trained context worker: {exc}")
            self._worker = None
            self._worker_ready = False
            return False

        try:
            ready_line = self._worker.stdout.readline().strip() if self._worker.stdout else ""
            payload = json.loads(ready_line) if ready_line else {}
            if payload.get("status") == "ready":
                self._worker_ready = True
                print(
                    "ClaimContextClassifier using persistent context worker:",
                    self.trained_checkpoint,
                    "on",
                    self.trained_device,
                )
                return True
        except Exception as exc:
            print(f"Context worker failed to initialize: {exc}")

        self._stop_worker()
        return False

    def _stop_worker(self) -> None:
        worker = self._worker
        self._worker = None
        self._worker_ready = False
        if worker is None:
            return
        try:
            if worker.stdin:
                worker.stdin.close()
        except Exception:
            pass
        try:
            worker.terminate()
            worker.wait(timeout=2)
        except Exception:
            try:
                worker.kill()
            except Exception:
                pass

    def classify(self, claim: str, original_claim: str | None = None, language: str | None = None) -> dict:
        if self.trained_checkpoint is not None:
            trained_result = self._classify_with_worker(claim, original_claim=original_claim, language=language)
            if trained_result is not None:
                return trained_result
        return self._model_unavailable_context(original_claim=original_claim, language=language)

    def _model_unavailable_context(self, original_claim: str | None = None, language: str | None = None) -> dict:
        # Non-heuristic fallback: keep context neutral when trained model output is unavailable.
        locality = self._detect_language_locality(language, (original_claim or "").lower())
        state_focus = None
        states = locality.get("states") or []
        if states:
            state_focus = str(states[0])
        return {
            "domain": "general_factual",
            "subcategory": "encyclopedic",
            "confidence": 0.0,
            "decision_source": "no_context_model_available",
            "risk_flags": ["regional_local_claim"] if state_focus else [],
            "state_focus": state_focus,
            "language": language or "unknown",
            "query_language": locality.get("query_language"),
            "region_hints": locality.get("countries", []),
            "original_claim": original_claim,
            "taxonomy_version": "v1",
            "available_domains": list(CONTEXT_TAXONOMY.keys()),
        }

    def _heuristic_classify(self, claim: str, original_claim: str | None = None, language: str | None = None) -> dict:
        claim_text = " ".join((claim or "").strip().lower().split())
        original_text = " ".join((original_claim or "").strip().lower().split())
        combined_text = " ".join(part for part in (claim_text, original_text) if part).strip()
        domain = "general_factual"
        subcategory = "encyclopedic"
        confidence = 0.3
        decision_source = "fallback_general"

        best_score = 0
        for domain_name, subcategories in DOMAIN_HINTS.items():
            for subcategory_name, hints in subcategories.items():
                score = sum(1 for hint in hints if self._hint_matches(combined_text, hint))
                if score > best_score:
                    best_score = score
                    domain = domain_name
                    subcategory = subcategory_name

        if best_score > 0:
            confidence = min(0.45 + (best_score * 0.12), 0.82)
            decision_source = "bootstrap_lexical_context"

        state_focus = self._detect_state_focus(combined_text, language=language)
        risk_flags = self._detect_risk_flags(combined_text, state_focus)
        locality = self._detect_language_locality(language, combined_text)

        if state_focus:
            confidence = max(confidence, 0.62)
        elif locality.get("countries"):
            confidence = max(confidence, 0.52)

        result = {
            "domain": domain,
            "subcategory": subcategory,
            "confidence": round(float(confidence), 3),
            "decision_source": decision_source,
            "risk_flags": risk_flags,
            "state_focus": state_focus,
            "language": language or "unknown",
            "query_language": locality.get("query_language"),
            "region_hints": locality.get("countries", []),
            "original_claim": original_claim,
            "taxonomy_version": "v1",
            "available_domains": list(CONTEXT_TAXONOMY.keys()),
        }
        return result

    def _best_subcategory_for_domain(self, claim_text: str, domain: str) -> str:
        subcategories = DOMAIN_HINTS.get(domain, {})
        best_subcategory = DOMAIN_TO_DEFAULT_SUBCATEGORY.get(domain, "encyclopedic")
        best_score = 0
        for subcategory_name, hints in subcategories.items():
            score = sum(1 for hint in hints if self._hint_matches(claim_text, hint))
            if score > best_score:
                best_score = score
                best_subcategory = subcategory_name
        return best_subcategory

    @staticmethod
    def _hint_matches(text: str, hint: str) -> bool:
        normalized_text = " ".join((text or "").strip().lower().split())
        normalized_hint = " ".join((hint or "").strip().lower().split())
        if not normalized_text or not normalized_hint:
            return False
        if " " in normalized_hint:
            return normalized_hint in normalized_text
        pattern = r"\b" + re.escape(normalized_hint) + r"\b"
        return re.search(pattern, normalized_text) is not None

    def _classify_with_worker(self, claim: str, original_claim: str | None = None, language: str | None = None):
        with self._worker_lock:
            if not self._start_worker():
                return None
            try:
                payload = json.dumps({"text": claim}, ensure_ascii=False)
                if not self._worker or not self._worker.stdin or not self._worker.stdout:
                    return None
                self._worker.stdin.write(payload + "\n")
                self._worker.stdin.flush()
                result_line = self._worker.stdout.readline().strip()
                if not result_line:
                    stderr = ""
                    if self._worker.stderr:
                        try:
                            stderr = self._worker.stderr.read(200)
                        except Exception:
                            stderr = ""
                    if stderr:
                        print(f"Trained context worker returned no output: {stderr}")
                    self._stop_worker()
                    return None
                payload = json.loads(result_line)
                if payload.get("error"):
                    print(f"Trained context worker error: {payload['error']}")
                    return None
            except Exception as exc:
                print(f"Trained context worker inference failed: {exc}")
                self._stop_worker()
                return None

        label = str(payload.get("label") or "general_factual").lower()
        confidence = float(payload.get("confidence") or 0.0)
        if confidence < self.MODEL_CONFIDENCE_THRESHOLD:
            fallback = self._model_unavailable_context(original_claim=original_claim, language=language)
            fallback["decision_source"] = "trained_context_low_confidence"
            fallback["model_domain"] = label
            fallback["model_confidence"] = round(confidence, 3)
            fallback["scores"] = payload.get("scores", {})
            return fallback

        claim_text = " ".join((claim or "").strip().lower().split())
        original_text = " ".join((original_claim or "").strip().lower().split())
        combined_text = " ".join(part for part in (claim_text, original_text) if part).strip()
        state_focus = self._detect_state_focus(combined_text, language=language)
        risk_flags = self._detect_risk_flags(combined_text, state_focus)
        locality = self._detect_language_locality(language, combined_text)
        result = {
            "domain": label,
            "subcategory": self._best_subcategory_for_domain(combined_text, label),
            "confidence": round(confidence, 3),
            "decision_source": "trained_context_model",
            "risk_flags": risk_flags,
            "state_focus": state_focus,
            "language": language or "unknown",
            "query_language": locality.get("query_language"),
            "region_hints": locality.get("countries", []),
            "original_claim": original_claim,
            "taxonomy_version": "v1",
            "available_domains": list(CONTEXT_TAXONOMY.keys()),
            "scores": payload.get("scores", {}),
        }
        return result

    def _detect_state_focus(self, claim_text: str, language: str | None = None) -> str | None:
        normalized_text = claim_text or ""
        for state_name, aliases in INDIA_STATE_ALIASES.items():
            for alias in aliases:
                pattern = r"\b" + re.escape(alias.lower()) + r"\b"
                if re.search(pattern, normalized_text):
                    return state_name
        if language == "te":
            if any(token in normalized_text for token in ("ఏపీలో", "ఏపీ", "ఆంధ్రప్రదేశ్", "ఆంధ్ర ప్రదేశ్")):
                return "andhra_pradesh"
            if any(token in normalized_text for token in ("తెలంగాణ", "టీఎస్", "హైదరాబాద్")):
                return "telangana"
        return None

    @staticmethod
    def _detect_language_locality(language: str | None, claim_text: str) -> dict:
        payload = LANGUAGE_LOCALITY_HINTS.get((language or "").strip().lower(), {})
        countries = list(payload.get("countries", [])) if payload else []
        states = list(payload.get("states", [])) if payload else []
        query_language = payload.get("query_language") if payload else None

        normalized = claim_text or ""
        if language == "te" and re.search(r"\bin ap\b", normalized):
            states = ["andhra_pradesh"]
        if language == "ta" and "chennai" in normalized:
            states = ["tamil_nadu"]

        return {
            "countries": countries,
            "states": states,
            "query_language": query_language,
        }

    @staticmethod
    def _detect_risk_flags(claim_text: str, state_focus: str | None) -> list[str]:
        flags = []
        if state_focus:
            flags.append("regional_local_claim")
        return flags
