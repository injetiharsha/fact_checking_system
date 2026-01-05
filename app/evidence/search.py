import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (FactCheckingBot)"
}

def search_web(query: str, max_results=5):
    """
    Uses DuckDuckGo HTML results (safe scraping).
    """
    url = "https://duckduckgo.com/html/"
    params = {"q": query}

    resp = requests.post(url, data=params, headers=HEADERS, timeout=5)
    soup = BeautifulSoup(resp.text, "html.parser")

    links = []
    for a in soup.select("a.result__a", limit=max_results):
        href = a.get("href")
        if href and href.startswith("http"):
            links.append(href)

    return links
