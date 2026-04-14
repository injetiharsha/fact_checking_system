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
        self.max_variants = max(1, min(6, int(os.getenv("SEARCH_PLANNER_MAX_VARIANTS", "5"))))

    def build_plan(self, claim, context_result=None, claim_type_result=None, original_claim=None, language=None):
        claim_text = " ".join((claim or "").strip().split())
        if not claim_text:
            return {"queries": []}

        context_result = context_result or {}
        resolved_language = str(language or "").strip().lower() or self._infer_language_from_script(claim_text) or "en"
        normalized_claim = self._normalize_claim_text(claim_text)
        plan = {
            "queries": [],
            "language": resolved_language,
            "country": None,
            "region": None,
            "recency_days": None,
            "intent_tags": [],
        }

        text_lower = normalized_claim.lower()
        original_query = " ".join((original_claim or "").strip().split())
        state_focus = str(context_result.get("state_focus") or "").strip().lower()
        region_hints = [str(item or "").strip().lower() for item in (context_result.get("region_hints") or []) if str(item or "").strip()]
        domain = str(context_result.get("domain") or "").strip().lower()
        subcategory = str(context_result.get("subcategory") or "").strip().lower()

        plan["country"] = self._infer_country(text_lower, region_hints)
        plan["region"] = state_focus or None
        plan["recency_days"] = self._infer_recency_days(text_lower, domain, subcategory)
        plan["intent_tags"] = self._infer_intent_tags(text_lower, domain, subcategory, plan["recency_days"])

        queries = [normalized_claim]
        if original_query and original_query != normalized_claim and plan["language"] != "en":
            queries.append(original_query)

        question_variant = self._question_variant(normalized_claim, plan["language"])
        if question_variant:
            queries.append(question_variant)

        keyword_variant = self._keyword_variant(normalized_claim)
        if keyword_variant:
            queries.append(keyword_variant)

        queries.extend(self._keyword_variants(normalized_claim, plan))
        queries.extend(self._official_variants(normalized_claim, plan, domain, subcategory))
        queries.extend(self._region_variants(normalized_claim, state_focus, region_hints))

        if plan["country"] == "in" and not any("india " in q.lower() for q in queries):
            queries.append(f"India {normalized_claim}")

        plan["queries"] = self._dedupe_queries(queries)[: self.max_variants]
        return plan

    @staticmethod
    def _normalize_claim_text(text):
        compact = " ".join((text or "").split()).strip()
        compact = compact.replace("“", "\"").replace("”", "\"").replace("’", "'")
        compact = re.sub(r"\s+([?.!,;:])", r"\1", compact)
        return compact

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

    def _official_variants(self, claim_text, plan, domain, subcategory):
        variants = []
        country = str(plan.get("country") or "").lower()
        lowered = claim_text.lower()
        if domain in {"government_public_policy", "business_economy"} or any(token in lowered for token in ("rbi", "minister", "policy", "law", "court", "government")):
            if country == "in":
                variants.append(f"site:rbi.org.in OR site:pib.gov.in {self._keyword_variant(claim_text) or claim_text}")
            else:
                variants.append(f"{claim_text} official")
        if domain in {"science", "space_astronomy"} or any(token in lowered for token in ("nasa", "space", "planet", "moon", "sun", "venus", "mars", "jupiter")):
            variants.append(f"site:nasa.gov {self._keyword_variant(claim_text) or claim_text}")
        if domain in {"health_medicine", "public_health"} or any(token in lowered for token in ("covid", "vaccine", "virus", "bleach", "health", "medical")):
            variants.append(f"site:who.int OR site:cdc.gov OR site:nih.gov {self._keyword_variant(claim_text) or claim_text}")
        if subcategory in {"elections", "policy", "weather_alerts"}:
            variants.append(f"{claim_text} official")
        return variants

    @staticmethod
    def _region_variants(claim_text, state_focus, region_hints):
        variants = []
        if state_focus:
            region_text = state_focus.replace("_", " ").strip()
            if region_text:
                variants.append(f"{region_text} {claim_text}")
        for hint in region_hints[:2]:
            hint = str(hint or "").strip()
            if hint:
                variants.append(f"{hint} {claim_text}")
        return variants

    @staticmethod
    def _question_variant(claim_text, language):
        compact = " ".join((claim_text or "").split()).strip()
        if not compact:
            return ""
        lowered = compact.lower()
        if compact.endswith("?"):
            return compact
        if language == "en":
            be_starts = ("is ", "are ", "was ", "were ", "has ", "have ", "had ", "can ", "could ", "will ", "did ", "does ", "do ")
            if lowered.startswith(be_starts):
                return compact + "?"
            subject_match = re.match(r"^([A-Z][^ ]*(?: [A-Z][^ ]*){0,3}) (is|are|was|were|has|have|had) (.+)$", compact)
            if subject_match:
                subj, verb, rest = subject_match.groups()
                return f"{verb.capitalize()} {subj} {rest}?"
            action_match = re.match(r"^([A-Z][^ ]*(?: [A-Z][^ ]*){0,4}) ([a-z]+ed|won|changed|launched|approved|announced|visited|signed) (.+)$", compact)
            if action_match:
                subj, verb, rest = action_match.groups()
                return f"Did {subj} {verb} {rest}?"
        return compact + "?"

    @staticmethod
    def _keyword_variant(claim_text):
        compact = " ".join((claim_text or "").split()).strip()
        if not compact:
            return ""
        tokens = re.findall(r"\b[\w'-]+\b", compact, flags=re.UNICODE)
        if not tokens:
            return ""
        stop = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "of", "in", "on", "at", "to", "for", "by", "with", "from", "that",
            "this", "these", "those", "and", "or", "but", "it", "as",
        }
        important = []
        for tok in tokens:
            low = tok.lower()
            if low in stop:
                continue
            if any(ch.isdigit() for ch in tok) or len(tok) >= 4 or tok[:1].isupper() or re.match(r"^(covid|rbi|nasa|dna|un|iss)$", low):
                important.append(tok)
        deduped = []
        seen = set()
        for tok in important:
            key = tok.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(tok)
        return " ".join(deduped[:8]).strip()

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
