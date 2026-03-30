# ingestion/webpage.py
from evidence.extraction_utils import fetch_and_extract


class WebpageIngestor:
    def extract_text(self, url):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            result = fetch_and_extract(
                url,
                headers,
                timeout=15,
                retries=2,
                verify=True,
                cache_dir="logs/extraction_cache",
            )
            print(
                "Webpage extraction:",
                result.get("extractor"),
                "| words:",
                result.get("word_count", 0),
                "| cache:",
                result.get("cache_hit", False),
                "| reject:",
                result.get("reject_reason"),
            )
            return (result.get("text") or "").strip()

        except Exception as e:
            print("Webpage ingestion error:", e)
            return ""
