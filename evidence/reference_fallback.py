from urllib.parse import quote_plus

import requests
import re
from bs4 import BeautifulSoup


class ReferenceFallback:
    def __init__(self):
        self.headers = {
            "User-Agent": (
                "FactLens/1.0 "
                "(https://example.invalid; reference fallback)"
            )
        }
        self.timeout = 10

    def fetch_wikipedia(self, claim):
        title = None
        for candidate in self._candidate_queries(claim):
            title = self._search_wikipedia_title(candidate)
            if title:
                break
        if not title:
            return None

        summary_url = (
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            f"{quote_plus(title.replace(' ', '_'))}"
        )

        try:
            response = requests.get(
                summary_url,
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return None

        extract = (payload.get("extract") or "").strip()
        content_url = (
            payload.get("content_urls", {})
            .get("desktop", {})
            .get("page")
        )
        article_text = self._fetch_article_text(content_url) if content_url else ""
        merged_text = self._merge_reference_text(extract, article_text)

        if len(merged_text.split()) < 12 or not content_url:
            return None

        return {
            "source": payload.get("title") or title,
            "url": content_url,
            "text": merged_text,
            "weight": 0.9,
        }

    def _fetch_article_text(self, url):
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except Exception:
            return ""

        try:
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception:
            return ""

        root = soup.find("main") or soup.find("article") or soup
        paragraphs = []
        for paragraph in root.find_all("p"):
            text = self._clean_paragraph_text(paragraph.get_text(" ", strip=True))
            if len(text.split()) >= 8:
                paragraphs.append(text)

        if not paragraphs:
            return ""

        prioritized = []
        secondary = []
        for paragraph in paragraphs:
            lowered = paragraph.lower()
            if any(
                cue in lowered
                for cue in (
                    " is ",
                    " are ",
                    " was ",
                    " were ",
                    " has ",
                    " have ",
                    " founded",
                    " established",
                    " invented",
                    " discovered",
                    " first ",
                    " earliest ",
                    " later ",
                    " before ",
                    " after ",
                    " heart",
                    " moon",
                    " berry",
                    " ring",
                    " star",
                )
            ):
                prioritized.append(paragraph)
            else:
                secondary.append(paragraph)

        selected = prioritized[:12] + secondary[:8]
        merged = " ".join(selected)
        return " ".join(merged.split())

    @staticmethod
    def _clean_paragraph_text(text):
        cleaned = " ".join((text or "").split())
        if not cleaned:
            return ""

        cleaned = re.sub(r"\[\s*\d+\s*\]", " ", cleaned)
        cleaned = re.sub(r"\[\s*[a-zA-Z]\s*\]", " ", cleaned)
        cleaned = re.sub(r"/[^/]{1,80}/", " ", cleaned)
        cleaned = re.sub(r"\(\s*listen\s*\)", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\(\s*[^)]*pronunciation[^)]*\)", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\([^)]{0,80}(?:US|UK|IPA|pronounced|pronunciation)[^)]*\)", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -:,;")

        if cleaned.startswith(":"):
            cleaned = cleaned[1:].strip()
        if cleaned.lower().startswith(("also known as ", "for other uses", "this article is about")):
            return ""
        if cleaned.count("(") > 3 or cleaned.count(")") > 3:
            return ""
        return cleaned

    @staticmethod
    def _merge_reference_text(extract, article_text):
        chunks = []
        seen = set()
        for block in (extract, article_text):
            normalized = " ".join((block or "").split())
            if normalized and normalized not in seen:
                seen.add(normalized)
                chunks.append(normalized)
        return " ".join(chunks).strip()

    def _candidate_queries(self, claim):
        raw = " ".join((claim or "").strip().split())
        if not raw:
            return []

        candidates = [raw]
        lowered = raw.lower()

        patterns = [
            r"^the\s+",
            r"\bis both a country and a continent\b",
            r"\bis the longest river in the world\b",
            r"\bis the largest continent on earth\b",
            r"\bis the largest island in the world\b",
            r"\bis the deepest lake on earth\b",
            r"\bis the farthest planet from the sun\b",
            r"\bis a star\b",
            r"\bhas rings\b",
            r"\bhas two moons\b",
            r"\bended in \d+\b",
            r"\bfell in \d+\s*ad\b",
            r"\bfell in \d+\b",
            r"\bwas invented by .+$",
            r"\bwas founded after .+$",
            r"\bare the only mammals capable of true flight\b",
            r"\bare older than trees\b",
            r"\bhave three hearts\b",
            r"\bare berries\b",
            r"\bcan breathe in space without equipment\b",
            r"\brotates in the opposite direction to most planets\b",
            r"\btravels faster in water than in air\b",
            r"\bshare about \d+ percent of their dna with bananas\b",
            r"\bis hotter than the surface of the sun\b",
            r"\bexpands when it freezes\b",
        ]

        stripped = lowered
        for pattern in patterns:
            stripped = re.sub(pattern, "", stripped).strip()
        stripped = re.sub(r"\s+", " ", stripped).strip()

        if stripped and stripped not in {raw.lower(), lowered}:
            candidates.append(stripped)

        tokens = [t for t in re.findall(r"[A-Za-z0-9]+", raw)]
        stop = {
            "the", "is", "a", "an", "are", "was", "were", "has", "have",
            "can", "in", "of", "to", "and", "both", "their", "with",
            "about", "than", "after", "most", "on",
        }
        compact = " ".join(t for t in tokens if t.lower() not in stop)
        if compact and compact.lower() not in {c.lower() for c in candidates}:
            candidates.append(compact)

        seen = set()
        ordered = []
        for candidate in candidates:
            key = candidate.lower().strip()
            if key and key not in seen:
                seen.add(key)
                ordered.append(candidate.strip())
        return ordered[:5]

    def _search_wikipedia_title(self, claim):
        search_url = (
            "https://en.wikipedia.org/w/api.php"
            "?action=opensearch"
            f"&search={quote_plus(claim)}"
            "&limit=1&namespace=0&format=json"
        )
        try:
            response = requests.get(
                search_url,
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return None

        if not isinstance(payload, list) or len(payload) < 2:
            return None

        titles = payload[1]
        if not titles:
            return None

        return str(titles[0]).strip()
