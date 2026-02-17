# evidence/scraper.py

import requests
from bs4 import BeautifulSoup


class WebScraper:

    def scrape(self, url):

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }

            response = requests.get(url, headers=headers, timeout=3)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "lxml")

            paragraphs = soup.find_all("p")

            if not paragraphs:
                return None

            text = " ".join(p.get_text() for p in paragraphs)

            return text.strip()

        except Exception as e:
            print("Scrape error:", e)
            return None
