import json
import re
import subprocess
import sys
from enum import Enum
from pathlib import Path

from training.common.config import runtime_model_settings


class ClaimCheckabilityLabel(Enum):
    CHECKABLE = "checkable"
    UNCHECKABLE = "uncheckable"


class ClaimCheckabilitySubtype(Enum):
    FACTUAL_CLAIM = "factual_claim"
    PERSONAL_STATEMENT = "personal_statement"
    OPINION = "opinion"
    QUESTION_OR_REWRITE = "question_or_rewrite"
    EMPTY = "empty"
    OTHER_UNCHECKABLE = "other_uncheckable"


class ClaimCheckabilityClassifier:
    """Checkability gate with a clean binary runtime output and richer subtypes."""

    MODEL_CONFIDENCE_THRESHOLD = 0.65

    def __init__(self):
        self.model_mode = "heuristic"
        self.trained_checkpoint = None
        self.trained_device = "cpu"
        self.helper_script = Path(__file__).with_name("checkability_subprocess_infer.py")

        runtime = runtime_model_settings("claim_checkability")
        checkpoint = runtime.get("checkpoint")
        if runtime.get("enabled") and checkpoint is not None:
            self.trained_checkpoint = Path(checkpoint)
            self.trained_device = runtime.get("device") or "cpu"
            self.model_mode = "trained_multiclass"
            print(
                "ClaimCheckabilityClassifier configured for trained checkpoint:",
                checkpoint,
            )

    def classify(self, claim: str, claim_type_result=None, logical_metadata=None) -> dict:
        if self.trained_checkpoint is not None:
            trained = self._classify_with_subprocess(claim)
            if trained is not None:
                if self._should_rescue_as_factual(
                    claim,
                    trained,
                    claim_type_result=claim_type_result,
                    logical_metadata=logical_metadata,
                ):
                    return self._build_result(
                        label=ClaimCheckabilityLabel.CHECKABLE,
                        subtype=ClaimCheckabilitySubtype.FACTUAL_CLAIM,
                        confidence=max(0.72, 1.0 - float(trained.get("confidence", 0.0))),
                        reasoning="Sentence-level factual cues overrode an 'other_uncheckable' gate prediction.",
                        code="checkable_factual_rescue",
                        message="",
                    )
                return trained
        return self._heuristic_classify(
            claim,
            claim_type_result=claim_type_result,
            logical_metadata=logical_metadata,
        )

    def _classify_with_subprocess(self, claim: str) -> dict | None:
        if self.trained_checkpoint is None:
            return None
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(self.helper_script),
                    "--checkpoint",
                    str(self.trained_checkpoint),
                    "--device",
                    str(self.trained_device),
                    "--text",
                    str(claim),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout.strip())
            raw_label = str(payload.get("label") or "uncheckable").lower()
            raw_subtype = str(payload.get("subtype") or "other_uncheckable").lower()
            confidence = float(payload.get("confidence", 0.0) or 0.0)
            label = ClaimCheckabilityLabel.CHECKABLE if raw_label == "checkable" else ClaimCheckabilityLabel.UNCHECKABLE
            subtype_map = {
                "factual_claim": ClaimCheckabilitySubtype.FACTUAL_CLAIM,
                "personal_statement": ClaimCheckabilitySubtype.PERSONAL_STATEMENT,
                "opinion": ClaimCheckabilitySubtype.OPINION,
                "question_or_rewrite": ClaimCheckabilitySubtype.QUESTION_OR_REWRITE,
                "empty": ClaimCheckabilitySubtype.EMPTY,
                "other_uncheckable": ClaimCheckabilitySubtype.OTHER_UNCHECKABLE,
            }
            subtype = subtype_map.get(raw_subtype, ClaimCheckabilitySubtype.OTHER_UNCHECKABLE)
            message_map = {
                ClaimCheckabilitySubtype.PERSONAL_STATEMENT: "This looks like a personal statement, not a fact-checkable claim.",
                ClaimCheckabilitySubtype.OPINION: "This reads more like an opinion than a checkable factual claim.",
                ClaimCheckabilitySubtype.QUESTION_OR_REWRITE: "Questions are not directly fact-checked. Rephrase it as a claim.",
                ClaimCheckabilitySubtype.EMPTY: "Enter a fact-checkable claim before analysis.",
                ClaimCheckabilitySubtype.OTHER_UNCHECKABLE: "This input is not a fact-checkable claim.",
            }
            code_map = {
                ClaimCheckabilitySubtype.PERSONAL_STATEMENT: "not_checkable_personal_statement",
                ClaimCheckabilitySubtype.OPINION: "opinion_not_checkable",
                ClaimCheckabilitySubtype.QUESTION_OR_REWRITE: "question_input",
                ClaimCheckabilitySubtype.EMPTY: "empty_claim",
                ClaimCheckabilitySubtype.OTHER_UNCHECKABLE: "not_checkable_other",
                ClaimCheckabilitySubtype.FACTUAL_CLAIM: "checkable",
            }
            return {
                "label": label,
                "subtype": subtype,
                "allowed": label == ClaimCheckabilityLabel.CHECKABLE,
                "confidence": confidence,
                "reasoning": "Fine-tuned claim checkability model prediction.",
                "decision_source": "trained_model",
                "code": code_map.get(subtype, "checkable"),
                "message": "" if label == ClaimCheckabilityLabel.CHECKABLE else message_map.get(subtype, "This input is not a fact-checkable claim."),
                "scores": payload.get("scores", {}),
            }
        except Exception:
            return None

    def _build_result(
        self,
        *,
        label: ClaimCheckabilityLabel,
        subtype: ClaimCheckabilitySubtype,
        confidence: float,
        reasoning: str,
        code: str,
        message: str,
    ) -> dict:
        return {
            "label": label,
            "subtype": subtype,
            "allowed": label == ClaimCheckabilityLabel.CHECKABLE,
            "confidence": float(confidence),
            "reasoning": reasoning,
            "decision_source": self.model_mode if self.model_mode != "heuristic" else "heuristic",
            "code": code,
            "message": message,
        }

    def _should_rescue_as_factual(self, claim: str, trained: dict, claim_type_result=None, logical_metadata=None) -> bool:
        if trained.get("label") != ClaimCheckabilityLabel.UNCHECKABLE:
            return False
        if trained.get("subtype") != ClaimCheckabilitySubtype.OTHER_UNCHECKABLE:
            return False

        claim_text = " ".join((claim or "").strip().split())
        lowered = claim_text.lower()
        if not claim_text or claim_text.endswith("?"):
            return False

        claim_type = str((claim_type_result or {}).get("type", "")).lower()
        if claim_type.endswith("opinion"):
            return False

        tokens = re.findall(r"\w+", lowered, flags=re.UNICODE)
        if len(tokens) < 4:
            return False

        if logical_metadata and logical_metadata.get("is_opinion"):
            return False

        factual_cues = (
            " is ",
            " are ",
            " was ",
            " were ",
            " has ",
            " have ",
            " had ",
            " became ",
            " become ",
            " can ",
            " cannot ",
            " cant ",
            " does ",
            " do ",
            " did ",
        )
        has_factual_cue = any(cue in f" {lowered} " for cue in factual_cues)
        has_digit = any(ch.isdigit() for ch in claim_text)
        has_non_ascii = any(ord(ch) > 127 for ch in claim_text)
        capitalized_entity = bool(re.search(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", claim))
        ends_like_statement = claim_text.endswith(".") or claim_text[-1].isalnum()
        native_script_factual_shape = has_non_ascii and has_digit and ends_like_statement

        return ends_like_statement and (has_factual_cue or has_digit or capitalized_entity or native_script_factual_shape)

    def _heuristic_classify(self, claim: str, claim_type_result=None, logical_metadata=None) -> dict:
        claim_text = " ".join((claim or "").strip().split())
        lowered = claim_text.lower()
        if not claim_text:
            return self._build_result(
                label=ClaimCheckabilityLabel.UNCHECKABLE,
                subtype=ClaimCheckabilitySubtype.EMPTY,
                confidence=0.99,
                reasoning="Empty input cannot be fact-checked.",
                code="empty_claim",
                message="Enter a fact-checkable claim before analysis.",
            )

        personal_patterns = (
            r"^this is me$",
            r"^this is us$",
            r"^this is mine$",
            r"^my name is",
            r"^i am",
            r"^i'm",
            r"^i feel",
            r"^i love",
            r"^i hate",
            r"^this is my",
        )
        if any(re.search(pattern, lowered) for pattern in personal_patterns):
            return self._build_result(
                label=ClaimCheckabilityLabel.UNCHECKABLE,
                subtype=ClaimCheckabilitySubtype.PERSONAL_STATEMENT,
                confidence=0.92,
                reasoning="Personal self-referential statement detected.",
                code="not_checkable_personal_statement",
                message="This looks like a personal statement, not a fact-checkable claim.",
            )

        if claim_text.endswith("?"):
            return self._build_result(
                label=ClaimCheckabilityLabel.UNCHECKABLE,
                subtype=ClaimCheckabilitySubtype.QUESTION_OR_REWRITE,
                confidence=0.9,
                reasoning="Question input should be rewritten as a claim.",
                code="question_input",
                message="Questions are not directly fact-checked. Rephrase it as a claim.",
            )

        claim_type = str((claim_type_result or {}).get("type", "")).lower()
        claim_type_conf = float((claim_type_result or {}).get("confidence", 0.0) or 0.0)
        if claim_type.endswith("opinion") and claim_type_conf >= 0.7:
            return self._build_result(
                label=ClaimCheckabilityLabel.UNCHECKABLE,
                subtype=ClaimCheckabilitySubtype.OPINION,
                confidence=claim_type_conf,
                reasoning="Opinion-heavy input detected.",
                code="opinion_not_checkable",
                message="This reads more like an opinion than a checkable factual claim.",
            )

        return self._build_result(
            label=ClaimCheckabilityLabel.CHECKABLE,
            subtype=ClaimCheckabilitySubtype.FACTUAL_CLAIM,
            confidence=0.75,
            reasoning="No strong non-checkable pattern detected.",
            code="checkable",
            message="",
        )
