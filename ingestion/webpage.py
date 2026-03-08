# ingestion/webpage.py

import requests
from bs4 import BeautifulSoup


class WebpageIngestor:
    def extract_text(self, url):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "form"]):
                tag.decompose()

            root = soup.find("article") or soup.find("main") or soup
            paragraphs = root.find_all("p")
            text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
            text = " ".join(text.split())

            return text.strip()

        except Exception as e:
            print("Webpage ingestion error:", e)
            return ""
