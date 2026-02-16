# ingestion/webpage.py

import requests
from bs4 import BeautifulSoup

class WebpageIngestor:
    def extract_text(self, url):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0"
            }

            response = requests.get(url, headers=headers, timeout=10)

            soup = BeautifulSoup(response.text, "lxml")

            paragraphs = soup.find_all("p")
            text = " ".join([p.get_text() for p in paragraphs])

            return text.strip()

        except Exception as e:
            print("Webpage ingestion error:", e)
            return ""
