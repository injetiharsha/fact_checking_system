import re
from urllib.parse import quote_plus

import requests


class NASAAPI:

    SEARCH_URL = "https://images-api.nasa.gov/search"
    TRUSTED_URL = "https://www.nasa.gov/"

    SPACE_KEYWORDS = {
        "nasa", "mars", "moon", "jupiter", "saturn", "sun", "planet", "planets",
        "solar system", "space", "astronomy", "astronaut", "rocket", "orbit",
        "galaxy", "star", "stars", "telescope", "apollo", "berlin wall",
    }

    def fetch(self, claim):
        if not self._is_space_claim(claim):
            return None

        try:
            response = requests.get(
                self.SEARCH_URL,
                params={"q": claim, "media_type": "image"},
                timeout=10,
            )
            if response.status_code != 200:
                return None

            payload = response.json() or {}
            items = ((payload.get("collection") or {}).get("items") or [])
            for item in items[:5]:
                data_rows = item.get("data") or []
                if not data_rows:
                    continue
                row = data_rows[0]
                title = (row.get("title") or "").strip()
                description = (row.get("description") or "").strip()
                nasa_id = (row.get("nasa_id") or "").strip()
                if not title and not description:
                    continue

                text = self._build_text(title, description)
                url = f"{self.TRUSTED_URL}search/{quote_plus(title or nasa_id or claim)}"
                return {
                    "source": "NASA",
                    "url": url,
                    "text": text,
                    "weight": 0.9,
                }
        except Exception as e:
            print("NASA API error:", e)
        return None

    def _is_space_claim(self, claim):
        claim_lower = (claim or "").lower()
        return any(keyword in claim_lower for keyword in self.SPACE_KEYWORDS)

    def _build_text(self, title, description):
        cleaned = re.sub(r"\s+", " ", description or "").strip()
        if cleaned:
            return f"{title}. {cleaned[:400]}".strip()
        return title
