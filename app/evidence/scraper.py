import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (FactCheckingBot)"
}

def scrape_article(url: str, max_chars=2000):
    """
    Extracts visible text from a webpage.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")

        # remove scripts/styles
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = " ".join(p.get_text() for p in soup.find_all("p"))
        return text[:max_chars]

    except Exception:
        return ""
