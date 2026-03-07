# evidence/scraper.py

import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WebScraper:

    def __init__(self):

        self.headers = {
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        }

        self.timeout = 6

    def scrape(self, url):

        print("\nScraping:", url)

        try:

            # Skip non HTML content
            if url.endswith(".pdf"):
                return None

            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                verify=False  # fixes SSL errors
            )

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            paragraphs = soup.find_all("p")

            text = " ".join(p.get_text() for p in paragraphs)

            text = text.strip()

            if len(text.split()) < 30:
                return None
            
            print("Scraped length:", len(text.split()), "words")
            print("Preview:", text[:200])

            return text
        


        except requests.exceptions.Timeout:
            return None

        except requests.exceptions.SSLError:
            return None

        except requests.exceptions.ConnectionError:
            return None

        except Exception:
            return None