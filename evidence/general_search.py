# evidence/general_search.py

from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class SearchEngine:

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
        self.timeout = 12

    def search(self, query, max_results=15):

        results = []
        search_url = (
            "https://html.duckduckgo.com/html/?q="
            f"{quote_plus(query)}"
        )

        try:
            response = requests.get(
                search_url,
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            links = soup.select("a.result__a")

            for link in links[:max_results]:
                href = (link.get("href") or "").strip()
                title = link.get_text(" ", strip=True)

                if not href or not title:
                    continue

                results.append({
                    "title": title,
                    "url": self._normalize_result_url(href),
                })

        except Exception as e:
            print(f"Search error: {type(e).__name__}: {e}")

        return results

    def _normalize_result_url(self, href):
        resolved = urljoin("https://html.duckduckgo.com", href)
        parsed = urlparse(resolved)

        if "duckduckgo.com" not in parsed.netloc:
            return resolved

        query = parse_qs(parsed.query)
        target = query.get("uddg", [None])[0]
        if target:
            return unquote(target)

        return resolved
