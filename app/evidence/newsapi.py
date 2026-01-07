import os
from newsapi import NewsApiClient

NEWS_API_KEY = os.getenv("NEWSAPI_KEY")

_newsapi_client = None
if NEWS_API_KEY:
    _newsapi_client = NewsApiClient(api_key=NEWS_API_KEY)


def fetch_newsapi(query: str, max_results: int = 5):
    if not _newsapi_client:
        return []

    results = []

    try:
        response = _newsapi_client.get_everything(
            q=query,
            language="en",
            sort_by="relevancy",
            page_size=max_results
        )

        for article in response.get("articles", []):
            title = article.get("title", "").strip()
            desc = article.get("description", "").strip()
            url = article.get("url")

            text = " ".join([t for t in [title, desc] if t])

            if not text or not url:
                continue

            results.append({
                "source": article.get("source", {}).get("name", "NewsAPI"),
                "url": url,
                "text": text
            })

    except Exception:
        return []

    return results
