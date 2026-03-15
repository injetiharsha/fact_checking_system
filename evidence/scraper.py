# evidence/scraper.py
import urllib3
from evidence.extraction_utils import fetch_and_extract
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
        result = self.scrape_with_metadata(url)
        return result.get("text") if result.get("ok") else None

    def scrape_with_metadata(self, url):

        print("\nScraping:", url)

        try:

            # Skip non HTML content
            if url.endswith(".pdf"):
                return {
                    "ok": False,
                    "text": "",
                    "extractor": "none",
                    "word_count": 0,
                    "cache_hit": False,
                    "reject_reason": "pdf_skipped",
                }

            result = fetch_and_extract(
                url,
                self.headers,
                timeout=self.timeout,
                retries=2,
                verify=False,
                cache_dir="logs/extraction_cache",
            )
            print(
                "Extraction:",
                result.get("extractor"),
                "| words:",
                result.get("word_count", 0),
                "| cache:",
                result.get("cache_hit", False),
                "| reject:",
                result.get("reject_reason"),
            )
            text = result.get("text") or ""
            if not result.get("ok") or not text:
                return result

            print("Scraped length:", len(text.split()), "words")
            print("Preview:", text[:200])

            return result

        except Exception:
            return {
                "ok": False,
                "text": "",
                "extractor": "none",
                "word_count": 0,
                "cache_hit": False,
                "reject_reason": "scrape_exception",
            }
