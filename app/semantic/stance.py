from transformers import pipeline

# Load once at startup
_nli = pipeline(
    task="zero-shot-classification",
    model="facebook/bart-large-mnli",
    device=0
)

LABELS = ["supports", "contradicts", "neutral"]


def _detect_stance(claim: str, evidence_text: str):
    """
    Internal NLI call.
    """
    if not claim or not evidence_text:
        return "neutral", 0.0

    result = _nli(
        sequences=evidence_text,
        candidate_labels=LABELS,
        hypothesis_template="This text {} the claim."
    )

    label = result["labels"][0]
    score = round(float(result["scores"][0]), 3)

    return label, score


def attach_stance(claim: str, evidence: dict) -> dict:
    """
    Attaches stance label and confidence directly to an evidence object.
    This is the ONLY function the pipeline should call.
    """
    label, score = _detect_stance(claim, evidence.get("text", ""))

    evidence["label"] = label
    evidence["confidence"] = score

    return evidence
