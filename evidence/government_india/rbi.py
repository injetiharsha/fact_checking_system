import re

import requests
from bs4 import BeautifulSoup


class RBIAPI:

    TOPIC_HINTS = {
        "inflation": "inflation statistics",
        "repo": "repo rate and monetary policy data",
        "interest": "interest rate statistics",
        "forex": "foreign exchange statistics",
        "currency": "currency and note issue data",
        "exchange rate": "exchange rate data",
    }

    _ws_re = re.compile(r"\s+")

    def fetch(self, claim):

        claim_lower = (claim or "").lower()
        topic = None
        for word, label in self.TOPIC_HINTS.items():
            if word in claim_lower:
                topic = label
                break

        if topic is None:
            return None

        try:
            url = "https://data.rbi.org.in/DBIE/dbie.rbi?site=statistics"
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                return None

            raw = response.text or ""
            try:
                soup = BeautifulSoup(raw, "lxml")
                page_text = self._ws_re.sub(" ", soup.get_text(separator=" ")).strip()
            except Exception:
                page_text = self._ws_re.sub(" ", raw).strip()

            if len(page_text) < 80:
                return None

            snippet = page_text[:800]
            final_url = getattr(response, "url", None) or "https://www.rbi.org.in/"

            return {
                "source": "Reserve Bank of India",
                "url": final_url,
                "text": (
                    f"RBI statistics portal (relevant topic: {topic}). "
                    f"Page text excerpt: {snippet}"
                ),
                "weight": 0.92,
            }

        except Exception as e:
            print("RBI API error:", e)
            return None
