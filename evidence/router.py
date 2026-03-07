import asyncio
import time
import os
import uuid

from evidence.international.worldbank import WorldBankAPI
from evidence.international.un_data import UNDataAPI
from evidence.government_india.rbi import RBIAPI
from evidence.government_india.mospi import MOSPIAPI
from evidence.international.who import WHOAPI
from evidence.international.oecd import OECDAPI
from evidence.trusted_news.news_api import TrustedNewsAPI

from evidence.general_search import SearchEngine
from evidence.scraper import WebScraper
from evidence.credibility_weights import get_weight


# domains that should never be scraped
BLOCKED_DOMAINS = [
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "reddit.com",
    "pinterest.com"
]


class EvidenceRouter:

    def __init__(self):

        # structured data APIs
        self.worldbank = WorldBankAPI()
        self.un_api = UNDataAPI()
        self.rbi = RBIAPI()
        self.mospi = MOSPIAPI()
        self.who = WHOAPI()
        self.oecd = OECDAPI()
        self.news_api = TrustedNewsAPI()

        # search + scraping
        self.search_engine = SearchEngine()
        self.scraper = WebScraper()

        # ensure log directory exists
        os.makedirs("logs/scraped_pages", exist_ok=True)

    async def get_evidence(self, claim, exclude_domain=None, trace=None):

        evidence_list = []

        # ----------------------------
        # 1. Structured APIs
        # ----------------------------

        api_start = time.time()

        api_tasks = [
            asyncio.to_thread(self.worldbank.fetch, claim),
            asyncio.to_thread(self.un_api.fetch, claim),
            asyncio.to_thread(self.rbi.fetch, claim),
            asyncio.to_thread(self.mospi.fetch, claim),
            asyncio.to_thread(self.who.fetch, claim),
            asyncio.to_thread(self.oecd.fetch, claim),
            asyncio.to_thread(self.news_api.fetch, claim)
        ]

        results = await asyncio.gather(*api_tasks, return_exceptions=True)

        for result in results:

            if isinstance(result, Exception):
                continue

            if not result:
                continue

            if isinstance(result, list):
                evidence_list.extend(result)
            else:
                evidence_list.append(result)

        print("Dynamic data:", round(time.time() - api_start, 3), "sec")

        # ----------------------------
        # 2. Web search fallback
        # ----------------------------

        search_start = time.time()

        search_results = self.search_engine.search(claim)[:15]

        print("\n--- SEARCH RESULTS ---")
        for r in search_results:
            print(r["title"])
            print(r["url"])

        scrape_jobs = []

        for result in search_results:

            url = result["url"]

            if exclude_domain and exclude_domain in url:
                continue

            if any(domain in url for domain in BLOCKED_DOMAINS):
                continue

            weight = get_weight(url)

            if weight == 0:
                continue

            scrape_jobs.append((result, url))

        # run scrapers concurrently
        scrape_tasks = [
            asyncio.to_thread(self.scraper.scrape, url)
            for _, url in scrape_jobs
        ]

        scraped_pages = await asyncio.gather(
            *scrape_tasks,
            return_exceptions=True
        )

        # combine results
        for (result, url), content in zip(scrape_jobs, scraped_pages):

            if isinstance(content, Exception):
                continue

            if not content:
                continue

            word_count = len(content.split())

            print("\nScraped:", url)
            print("Words:", word_count)
            print("Preview:", content[:200])

            # save page to file
            page_id = str(uuid.uuid4())[:8]
            filename = f"logs/scraped_pages/page_{page_id}.txt"

            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)

            # add to trace
            if trace is not None:

                trace["scraped_pages"].append({
                    "url": url,
                    "title": result["title"],
                    "word_count": word_count,
                    "file": filename,
                    "preview": content[:200]
                })

            evidence_list.append({
                "source": result["title"],
                "url": url,
                "text": content,
                "weight": get_weight(url)
            })

        print("Search results:", round(time.time() - search_start, 3), "sec")

        # ----------------------------
        # 3. Remove duplicate URLs
        # ----------------------------

        seen = set()
        unique_evidence = []

        for ev in evidence_list:

            url = ev["url"]

            if url in seen:
                continue

            seen.add(url)
            unique_evidence.append(ev)

        return unique_evidence