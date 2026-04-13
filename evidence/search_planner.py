import os
import re


COUNTRY_GL_MAP = {
    "india": "in",
    "united states": "us",
    "usa": "us",
    "us": "us",
    "united kingdom": "uk",
    "uk": "uk",
    "canada": "ca",
    "australia": "au",
}


LANGUAGE_HL_MAP = {
    "en": "en",
    "hi": "hi",
    "ta": "ta",
    "te": "te",
    "kn": "kn",
    "ml": "ml",
}


class SearchPlanner:
    def __init__(self):
        self.max_variants = max(1, min(4, int(os.getenv("SEARCH_PLANNER_MAX_VARIANTS", "3"))))

    def build_plan(self, claim, context_result=None, claim_type_result=None, original_claim=None, language=None):
        claim_text = " ".join((claim or "").strip().split())
        if not claim_text:
            return {"queries": []}

        context_result = context_result or {}
        resolved_language = str(language or "").strip().lower() or self._infer_language_from_script(claim_text) or "en"
        plan = {
            "queries": [],
            "language": resolved_language,
            "country": None,
            "region": None,
            "recency_days": None,
            "intent_tags": [],
        }

        text_lower = claim_text.lower()
        original_query = " ".join((original_claim or "").strip().split())
        state_focus = str(context_result.get("state_focus") or "").strip().lower()
        region_hints = [str(item or "").strip().lower() for item in (context_result.get("region_hints") or []) if str(item or "").strip()]
        domain = str(context_result.get("domain") or "").strip().lower()
        subcategory = str(context_result.get("subcategory") or "").strip().lower()

        plan["country"] = self._infer_country(text_lower, region_hints)
        plan["region"] = state_focus or None
        plan["recency_days"] = self._infer_recency_days(text_lower, domain, subcategory)
        plan["intent_tags"] = self._infer_intent_tags(text_lower, domain, subcategory, plan["recency_days"])

        queries = [claim_text]
        if original_query and original_query != claim_text and plan["language"] != "en":
            queries.append(original_query)

        queries.extend(self._keyword_variants(claim_text, plan))

        if plan["country"] == "in" and not any("india " in q.lower() for q in queries):
            queries.append(f"India {claim_text}")
        if state_focus:
            region_text = state_focus.replace("_", " ").strip()
            if region_text:
                queries.append(f"{region_text} {claim_text}")

        plan["queries"] = self._dedupe_queries(queries)[: self.max_variants]
        return plan

    @staticmethod
    def _infer_language_from_script(text):
        sample = str(text or "")
        if any("\u0b80" <= ch <= "\u0bff" for ch in sample):
            return "ta"
        if any("\u0c00" <= ch <= "\u0c7f" for ch in sample):
            return "te"
        if any("\u0d00" <= ch <= "\u0d7f" for ch in sample):
            return "ml"
        if any("\u0c80" <= ch <= "\u0cff" for ch in sample):
            return "kn"
        if any("\u0900" <= ch <= "\u097f" for ch in sample):
            return "hi"
        return None

    def _infer_country(self, text_lower, region_hints):
        for hint in region_hints:
            if hint in {"india", "indian"}:
                return "in"
            if hint in {"us", "usa", "united states", "america"}:
                return "us"
        for phrase, gl in COUNTRY_GL_MAP.items():
            if phrase in text_lower:
                return gl
        return None

    def _infer_recency_days(self, text_lower, domain, subcategory):
        if any(token in text_lower for token in ("today", "right now", "currently", "at present")):
            return 1
        if any(token in text_lower for token in ("yesterday", "this morning", "this evening")):
            return 2
        if any(token in text_lower for token in ("this week", "last week")):
            return 7
        if any(token in text_lower for token in ("this month", "last month", "recently", "latest", "new", "newly")):
            return 30
        if any(token in text_lower for token in ("this year", "last year")):
            return 365
        if domain in {"sports", "business_economy", "government_public_policy", "weather_climate"}:
            return 30
        if subcategory in {"stock_market", "earnings", "elections", "policy", "weather_alerts"}:
            return 30
        return None

    def _infer_intent_tags(self, text_lower, domain, subcategory, recency_days):
        tags = []
        if recency_days is not None:
            tags.append("time_sensitive")
        if any(token in text_lower for token in ("match", "score", "won", "league", "tournament", "goal")) or domain == "sports":
            tags.append("sports")
        if any(token in text_lower for token in ("stock", "shares", "revenue", "profit", "inflation", "gdp", "repo rate")) or domain == "business_economy":
            tags.append("business")
        if any(token in text_lower for token in ("minister", "government", "policy", "law", "court", "article ", "constitution", "rbi")) or domain == "government_public_policy":
            tags.append("government")
        if any(token in text_lower for token in ("rain", "storm", "alert", "cyclone", "weather", "heatwave")) or domain == "weather_climate":
            tags.append("weather")
        if any(token in text_lower for token in ("fake", "hoax", "myth", "debunk", "cures", "causes", "spread")):
            tags.append("misinformation")
        return tags

    def _keyword_variants(self, claim_text, plan):
        variants = []
        text_lower = claim_text.lower()

        if plan.get("recency_days") == 1 and "today" not in text_lower:
            variants.append(f"{claim_text} today")
        elif plan.get("recency_days") == 7 and "this week" not in text_lower and "last week" not in text_lower:
            variants.append(f"{claim_text} this week")
        elif plan.get("recency_days") == 30 and "latest" not in text_lower and "recent" not in text_lower:
            variants.append(f"{claim_text} latest")

        year_matches = re.findall(r"\b(19\d{2}|20\d{2})\b", text_lower)
        if year_matches:
            variants.append(f"{claim_text} {year_matches[0]}")

        if "misinformation" in plan.get("intent_tags", []):
            variants.append(f"{claim_text} fact check")
            variants.append(f"{claim_text} debunked")

        if "government" in plan.get("intent_tags", []):
            variants.append(f"{claim_text} official")

        if "business" in plan.get("intent_tags", []):
            variants.append(f"{claim_text} report")

        if "sports" in plan.get("intent_tags", []):
            variants.append(f"{claim_text} official")

        return variants

    @staticmethod
    def _dedupe_queries(queries):
        seen = set()
        ordered = []
        for query in queries:
            compact = re.sub(r"\s+", " ", str(query or "")).strip()
            key = compact.lower()
            if compact and key not in seen:
                seen.add(key)
                ordered.append(compact)
        return ordered
