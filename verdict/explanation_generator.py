# verdict/explanation_generator.py

from typing import Dict, List, Optional


def _clean_text(value: str, max_len: int = 220) -> str:
    text = " ".join((value or "").split()).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _top_sources(evidence_list: List[Dict], stance: str, max_items: int = 3) -> List[str]:
    sources: List[str] = []
    for ev in evidence_list:
        if ev.get("stance") != stance:
            continue
        source = str(ev.get("source") or "").strip()
        if not source or source == "logic_engine":
            continue
        if source not in sources:
            sources.append(source)
        if len(sources) >= max_items:
            break
    return sources


def _best_snippet(evidence_list: List[Dict], stance: str) -> str:
    candidates = [ev for ev in evidence_list if ev.get("stance") == stance and ev.get("text")]
    if not candidates:
        return ""
    ranked = sorted(
        candidates,
        key=lambda ev: (
            float(ev.get("relevance_score", 0)) * float(ev.get("quality_score", 0)),
            float(ev.get("confidence", 0)),
            float(ev.get("weight", 0)),
        ),
        reverse=True,
    )
    return _clean_text(str(ranked[0].get("text") or ""))


def generate_explanation(
    claim: str,
    evidence_list: List[Dict],
    verdict: str,
    confidence: float,
    conflict_summary: Optional[str] = None,
) -> str:
    support_count = sum(1 for ev in evidence_list if ev.get("stance") == "SUPPORT")
    refute_count = sum(1 for ev in evidence_list if ev.get("stance") == "REFUTE")
    neutral_count = sum(1 for ev in evidence_list if ev.get("stance") == "NEUTRAL")

    support_sources = _top_sources(evidence_list, "SUPPORT")
    refute_sources = _top_sources(evidence_list, "REFUTE")
    support_snippet = _best_snippet(evidence_list, "SUPPORT")
    refute_snippet = _best_snippet(evidence_list, "REFUTE")

    lines: List[str] = []
    lines.append(f'The claim "{_clean_text(claim, 140)}" was evaluated against available evidence.')
    lines.append(
        f"Evidence balance: {support_count} supporting, {refute_count} contradicting, "
        f"and {neutral_count} neutral items."
    )

    if verdict == "TRUE":
        lines.append("The evidence aligns with the claim more strongly than it contradicts it.")
        if support_sources:
            lines.append(f"Key supporting sources include {', '.join(support_sources)}.")
        if support_snippet:
            lines.append(f'Strong supporting point: "{support_snippet}"')
        if refute_snippet:
            lines.append(f'Some contradictory context exists: "{refute_snippet}"')
    elif verdict == "FALSE":
        lines.append("The evidence contradicts the claim more strongly than it supports it.")
        if refute_sources:
            lines.append(f"Key contradicting sources include {', '.join(refute_sources)}.")
        if refute_snippet:
            lines.append(f'Strong contradicting point: "{refute_snippet}"')
        if support_snippet:
            lines.append(f'Some supporting context exists: "{support_snippet}"')
    else:
        lines.append("The evidence is mixed or not strong enough for a definitive conclusion.")
        if support_snippet:
            lines.append(f'Supporting side: "{support_snippet}"')
        if refute_snippet:
            lines.append(f'Contradicting side: "{refute_snippet}"')

    lines.append(f"Confidence level: {round(float(confidence) * 100, 1)}%.")

    cleaned_conflict = _clean_text(conflict_summary or "", 180)
    if cleaned_conflict:
        lines.append(f"Conflict assessment: {cleaned_conflict}.")

    return " ".join(lines)
