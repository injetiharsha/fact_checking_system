# evidence/scraper.py

import requests
from bs4 import BeautifulSoup
import random


class WebScraper:

    def scrape(self, url):

        try:
            USER_AGENTS = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605 Safari/605.1.15",
            ]
            headers = {
                "User-Agent": random.choice(USER_AGENTS)
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
