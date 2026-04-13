import os
import time

import requests

from config import NEWS_API_KEYS


class TrustedNewsAPI:
    NEWSDATA_URL = "https://newsdata.io/api/1/latest"
    NEWSAPI_ORG_URL = "https://newsapi.org/v2/everything"

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

    def __init__(self):
        self._backoff_until = 0.0
        self.api_keys = list(NEWS_API_KEYS)
        self._api_key_index = 0
        self.newsapi_org_key = (os.getenv("NEWSAPI_ORG_KEY") or os.getenv("NEWS_API_KEY") or "").strip()

    def fetch(self, claim):
        if time.time() < self._backoff_until:
            return []

        rows = self._fetch_newsdata(claim)
        if rows:
            return self._dedupe_evidence(rows)

        rows = self._fetch_newsapi_org(claim)
        return self._dedupe_evidence(rows)

    def _fetch_newsdata(self, claim):
        api_key = self._next_api_key()
        if not api_key:
            return []

        params = {
            "q": claim,
            "language": "en",
            "apikey": api_key,
        }

        try:
            response = requests.get(self.NEWSDATA_URL, params=params, timeout=10)
            if response.status_code != 200:
                print("NewsData API error:", response.status_code, response.text[:300])
                if response.status_code in {401, 403, 429}:
                    self._backoff_until = time.time() + 900
                return []

            data = response.json()
            articles = data.get("results", [])
            evidence_list = []

            for article in articles:
                url = article.get("link", "") or article.get("url", "")
                if not self._is_trusted_url(url):
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
                    "weight": 0.85,
                })

            return evidence_list

        except Exception as e:
            print("NewsData API error:", e)
            if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                self._backoff_until = time.time() + 180
            return []

    def _fetch_newsapi_org(self, claim):
        if not self.newsapi_org_key:
            return []

        params = {
            "q": claim,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": 10,
            "apiKey": self.newsapi_org_key,
        }

        try:
            response = requests.get(self.NEWSAPI_ORG_URL, params=params, timeout=10)
            if response.status_code != 200:
                print("NewsAPI.org error:", response.status_code, response.text[:300])
                if response.status_code in {401, 403, 429}:
                    self._backoff_until = time.time() + 900
                return []

            data = response.json() or {}
            evidence_list = []
            for article in data.get("articles", []):
                url = article.get("url", "")
                if not self._is_trusted_url(url):
                    continue

                source_name = (
                    ((article.get("source") or {}).get("name"))
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
                    "weight": 0.85,
                })
            return evidence_list

        except Exception as e:
            print("NewsAPI.org error:", e)
            if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                self._backoff_until = time.time() + 180
            return []

    def _next_api_key(self):
        if not self.api_keys:
            return ""
        key = self.api_keys[self._api_key_index % len(self.api_keys)]
        self._api_key_index = (self._api_key_index + 1) % len(self.api_keys)
        return key

    def _is_trusted_url(self, url):
        return any(domain in (url or "") for domain in self.TRUSTED_DOMAINS)

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
