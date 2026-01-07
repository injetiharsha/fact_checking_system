import requests

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"

def fetch_gdelt_news(query: str, max_results=5):
    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": max_results,
        "timespan": "30d"
    }

    try:
        resp = requests.get(GDELT_API, params=params, timeout=5)
        data = resp.json()

        results = []
        for art in data.get("articles", []):
            results.append({
                "source": art.get("sourceCountry", "GDELT"),
                "url": art.get("url"),
                "text": art.get("title", "")
            })
        return results
    except Exception:
        return []
