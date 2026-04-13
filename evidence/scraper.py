# evidence/scraper.py
import os

import requests
from evidence.extraction_utils import fetch_and_extract

class WebScraper:

    def __init__(self):

        self.headers = {
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        }

        self.timeout = 6
        self.allow_insecure_retry = os.getenv("ALLOW_INSECURE_SCRAPE_RETRY", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.cache_extraction = os.getenv("FACTLENS_CACHE_EXTRACTION", "0").strip().lower() in {"1", "true", "yes", "on"}

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
                verify=True,
                cache_dir="logs/extraction_cache" if self.cache_extraction else None,
            )
            if (
                self.allow_insecure_retry
                and not result.get("ok")
                and str(result.get("reject_reason") or "").startswith("fetch_error:SSLError")
            ):
                result = fetch_and_extract(
                    url,
                    self.headers,
                    timeout=self.timeout,
                    retries=1,
                    verify=False,
                    cache_dir="logs/extraction_cache_insecure" if self.cache_extraction else None,
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

        except requests.RequestException:
            return {
                "ok": False,
                "text": "",
                "extractor": "none",
                "word_count": 0,
                "cache_hit": False,
                "reject_reason": "scrape_request_exception",
            }
        except Exception:
            return {
                "ok": False,
                "text": "",
                "extractor": "none",
                "word_count": 0,
                "cache_hit": False,
                "reject_reason": "scrape_exception",
            }
