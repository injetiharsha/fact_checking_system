import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "FactCheckingSystem/1.0"
}

def scrape_article(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        paragraphs = [
            p.get_text().strip()
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) > 80
        ]

        return " ".join(paragraphs[:3])

    except Exception:
        return ""
