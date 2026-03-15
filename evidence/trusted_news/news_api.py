import os
import requests
from config import NEWS_API_KEY


class TrustedNewsAPI:

    BASE_URL = "https://newsdata.io/api/1/latest"

    TRUSTED_DOMAINS = [
        "reuters.com",
        "bbc.co.uk",
        "bbc.com",
        "thehindu.com",
        "indianexpress.com",
        "apnews.com",
        "finance.yahoo.com",
        "marketwatch.com",
        "cnbc.com",
        "bloomberg.com",
    ]

    def fetch(self, claim):
        return self._dedupe_evidence(self._fetch_newsdata(claim))

    def _fetch_newsdata(self, claim):
        if not NEWS_API_KEY:
            return []

        params = {
            "q": claim,
            "language": "en",
            "apikey": NEWS_API_KEY,
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            if response.status_code != 200:
                print("News API error:", response.status_code, response.text[:300])
                return []

            data = response.json()
            articles = data.get("results", [])
            evidence_list = []

            for article in articles:
                url = article.get("link", "") or article.get("url", "")

                if not any(domain in url for domain in self.TRUSTED_DOMAINS):
                    continue

                source_name = (
                    article.get("source_name")
                    or article.get("source_id")
                    or "Trusted News"
                )
                text = (
                    article.get("description", "")
                    or article.get("title", "")
                    or article.get("content", "")
                )
                if not text:
                    continue

                evidence_list.append({
                    "source": source_name,
                    "url": url,
                    "text": text,
                    "weight": 0.85
                })

            return evidence_list

        except Exception as e:
            print("News API error:", e)
            return []

    def _dedupe_evidence(self, rows):
        deduped = []
        seen = set()
        for row in rows:
            key = ((row.get("url") or "").strip(), (row.get("text") or "").strip())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        return deduped
