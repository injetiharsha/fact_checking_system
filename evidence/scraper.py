# evidence/scraper.py

import requests
from bs4 import BeautifulSoup

class WebScraper:
    def scrape(self, url):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                return ""

            soup = BeautifulSoup(response.text, "lxml")

            paragraphs = soup.find_all("p")
            text = " ".join([p.get_text() for p in paragraphs])

            return text.strip()

        except Exception as e:
            print("Scrape error:", e)
            return ""
