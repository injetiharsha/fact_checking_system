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


def _source_phrase(items: List[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


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
    cleaned_conflict = _clean_text(conflict_summary or "", 180)

    verdict = str(verdict or "NEUTRAL").upper()
    claim_text = _clean_text(claim, 140)
    confidence_pct = round(float(confidence) * 100, 1)

    lines: List[str] = []

    if verdict == "TRUE":
        lines.append(f'The claim "{claim_text}" is rated TRUE because the strongest evidence supports it.')
        if support_snippet:
            lines.append(f'The clearest supporting evidence says: "{support_snippet}"')
        if support_sources:
            lines.append(f'This conclusion is supported by sources such as {_source_phrase(support_sources)}.')
        lines.append(f'The evidence mix was {support_count} supporting, {refute_count} contradicting, and {neutral_count} neutral items, with an overall confidence of {confidence_pct}%.')
        if refute_snippet:
            lines.append(f'Conflicting context was also found, but it was weaker overall: "{refute_snippet}"')
    elif verdict == "FALSE":
        lines.append(f'The claim "{claim_text}" is rated FALSE because the strongest evidence contradicts it.')
        if refute_snippet:
            lines.append(f'The clearest contradictory evidence says: "{refute_snippet}"')
        if refute_sources:
            lines.append(f'This conclusion is supported by sources such as {_source_phrase(refute_sources)}.')
        lines.append(f'The evidence mix was {support_count} supporting, {refute_count} contradicting, and {neutral_count} neutral items, with an overall confidence of {confidence_pct}%.')
        if support_snippet:
            lines.append(f'Some supporting context appeared, but it was weaker overall: "{support_snippet}"')
    else:
        lines.append(f'The claim "{claim_text}" is rated NEUTRAL because the evidence was mixed or not decisive enough.')
        lines.append(f'The evidence mix was {support_count} supporting, {refute_count} contradicting, and {neutral_count} neutral items, with an overall confidence of {confidence_pct}%.')
        if support_snippet:
            lines.append(f'Best supporting evidence: "{support_snippet}"')
        if refute_snippet:
            lines.append(f'Best contradictory evidence: "{refute_snippet}"')

    if cleaned_conflict:
        lines.append(f'Conflict assessment: {cleaned_conflict}.')

    return " ".join(lines)
