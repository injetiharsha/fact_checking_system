from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


def _normalize_token(token: str) -> str:
    token = (token or "").lower().strip(".,;:!?()[]{}\"'")
    digit_map = {
        "0": "zero",
        "1": "one",
        "2": "two",
        "3": "three",
        "4": "four",
        "5": "five",
        "6": "six",
        "7": "seven",
        "8": "eight",
        "9": "nine",
        "10": "ten",
    }
    token = digit_map.get(token, token)
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("es") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def _token_set(text: str) -> set[str]:
    tokens = set()
    for raw in (text or "").lower().split():
        normalized = _normalize_token(raw)
        if normalized:
            tokens.add(normalized)
    return tokens


@dataclass
class SessionCacheEntry:
    claim: str
    claim_tokens: set[str]
    domain: str
    evidence_rows: List[Dict]


@dataclass
class SessionRetrievalCache:
    min_similarity: float = 0.6
    max_entries: int = 24
    _entries: List[SessionCacheEntry] = field(default_factory=list)

    def lookup(self, claim: str, context_result: Dict | None = None, max_items: int = 2) -> Tuple[List[Dict], Dict]:
        claim_tokens = _token_set(claim)
        domain = str((context_result or {}).get("domain") or "")
        if not claim_tokens:
            return [], {"lookup_claims_checked": 0, "matched_claims": 0, "returned_items": 0}

        matches: List[Tuple[float, SessionCacheEntry]] = []
        for entry in self._entries:
            similarity = self._similarity(claim_tokens, entry.claim_tokens)
            if similarity < self.min_similarity:
                continue
            if domain and entry.domain and domain != entry.domain:
                continue
            matches.append((similarity, entry))

        matches.sort(key=lambda item: item[0], reverse=True)

        seen = set()
        rows: List[Dict] = []
        for similarity, entry in matches:
            for ev in entry.evidence_rows:
                dedupe_key = ((ev.get("url") or "").strip(), " ".join((ev.get("text") or "").split()))
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                cached = dict(ev)
                cached["source"] = ev.get("source")
                cached["session_cache_hit"] = True
                cached["session_cache_similarity"] = round(float(similarity), 3)
                cached["session_cache_from_claim"] = entry.claim
                rows.append(cached)
                if len(rows) >= max_items:
                    break
            if len(rows) >= max_items:
                break

        stats = {
            "lookup_claims_checked": len(self._entries),
            "matched_claims": len(matches),
            "returned_items": len(rows),
        }
        return rows, stats

    def store(self, claim: str, context_result: Dict | None, evidence_rows: List[Dict]) -> Dict:
        domain = str((context_result or {}).get("domain") or "")
        claim_tokens = _token_set(claim)
        kept_rows: List[Dict] = []
        seen = set()

        for ev in evidence_rows:
            if not self._eligible(ev):
                continue
            dedupe_key = ((ev.get("url") or "").strip(), " ".join((ev.get("text") or "").split()))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            kept_rows.append({
                "source": ev.get("source"),
                "url": ev.get("url"),
                "text": ev.get("text"),
                "context_text": ev.get("context_text") or ev.get("text"),
                "weight": float(ev.get("weight", 0.0) or 0.0),
                "raw_weight": float(ev.get("raw_weight", ev.get("weight", 0.0)) or 0.0),
                "relevance_score": float(ev.get("relevance_score", 0.0) or 0.0),
                "base_relevance_score": float(ev.get("base_relevance_score", ev.get("relevance_score", 0.0)) or 0.0),
                "selector_score": float(ev.get("selector_score", 0.0) or 0.0),
                "quality_score": float(ev.get("quality_score", 0.0) or 0.0),
                "combined_score": float(ev.get("combined_score", 0.0) or 0.0),
                "evidence_tier": ev.get("evidence_tier", "soft"),
            })
            if len(kept_rows) >= 3:
                break

        if not claim_tokens or not kept_rows:
            return {"stored_items": 0, "cache_entries": len(self._entries)}

        self._entries = [
            entry for entry in self._entries
            if " ".join(entry.claim.lower().split()) != " ".join((claim or "").lower().split())
        ]
        self._entries.insert(0, SessionCacheEntry(claim=claim, claim_tokens=claim_tokens, domain=domain, evidence_rows=kept_rows))
        self._entries = self._entries[: self.max_entries]

        return {"stored_items": len(kept_rows), "cache_entries": len(self._entries)}

    @staticmethod
    def _eligible(ev: Dict) -> bool:
        if not ev or ev.get("url", "").startswith("internal://"):
            return False
        if str(ev.get("evidence_tier") or "").lower() != "strong":
            return False
        if float(ev.get("relevance_score", 0.0) or 0.0) < 0.72:
            return False
        if float(ev.get("quality_score", 0.0) or 0.0) < 0.45:
            return False
        if float(ev.get("weight", 0.0) or 0.0) < 0.45:
            return False
        text = (ev.get("text") or "").strip()
        return len(text.split()) >= 8

    @staticmethod
    def _similarity(left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        intersection = len(left & right)
        union = len(left | right)
        return intersection / max(union, 1)
