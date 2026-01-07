import requests

DDG_API = "https://api.duckduckgo.com/"

HEADERS = {
    "User-Agent": "FactCheckingSystem/1.0"
}

def search_web(query: str, max_results: int = 5):
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1
    }

    urls = []

    try:
        r = requests.get(
            DDG_API,
            params=params,
            headers=HEADERS,
            timeout=5
        )
        r.raise_for_status()
        data = r.json()

        for item in data.get("RelatedTopics", []):
            if isinstance(item, dict) and "FirstURL" in item:
                urls.append(item["FirstURL"])
                if len(urls) >= max_results:
                    break

    except Exception as e:
        # IMPORTANT: do not silently fail
        # Let fetcher metrics handle zero-result cases
        return []

    return urls
