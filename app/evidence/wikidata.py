import requests

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"

HEADERS = {
    "User-Agent": "FactCheckingSystem/1.0"
}

async def fetch_wikipedia_evidence(query: str):
    results = []

    title = query.replace(" ", "_")

    try:
        r = requests.get(
            WIKI_API.format(title),
            headers=HEADERS,
            timeout=5
        )

        if r.status_code != 200:
            return []

        data = r.json()

        extract = data.get("extract")
        if not extract:
            return []

        results.append({
            "source": "Wikipedia",
            "url": data.get("content_urls", {})
                     .get("desktop", {})
                     .get("page"),
            "text": extract
        })

    except Exception:
        return []

    return results
