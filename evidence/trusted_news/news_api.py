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
        "apnews.com"
    ]

    def fetch(self, claim):

        params = {
            "q": claim,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": 5,
            "apiKey": NEWS_API_KEY
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)

            if response.status_code != 200:
                return []

            data = response.json()

            articles = data.get("articles", [])
            evidence_list = []

            for article in articles:
                url = article.get("url", "")

                if not any(domain in url for domain in self.TRUSTED_DOMAINS):
                    continue

                evidence_list.append({
                    "source": article.get("source", {}).get("name", "Trusted News"),
                    "url": url,
                    "text": article.get("description", "") or article.get("title", ""),
                    "weight": 0.85
                })

            return evidence_list

        except Exception as e:
            print("News API error:", e)
            return []
