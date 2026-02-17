import asyncio
import time
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


class EvidenceRouter:

    def __init__(self):
        self.worldbank = WorldBankAPI()
        self.un_api = UNDataAPI()
        self.rbi = RBIAPI()
        self.mospi = MOSPIAPI()
        self.who = WHOAPI()
        self.oecd = OECDAPI()
        self.news_api = TrustedNewsAPI()

        self.search_engine = SearchEngine()
        self.scraper = WebScraper()

    async def get_evidence(self, claim, exclude_domain=None):

        evidence_list = []

        # ---- RUN STRUCTURED APIs IN PARALLEL ----

        tasks = [
            asyncio.to_thread(self.worldbank.fetch, claim),
            asyncio.to_thread(self.un_api.fetch, claim),
            asyncio.to_thread(self.rbi.fetch, claim),
            asyncio.to_thread(self.mospi.fetch, claim),
            asyncio.to_thread(self.who.fetch, claim),
            asyncio.to_thread(self.oecd.fetch, claim),
            asyncio.to_thread(self.news_api.fetch, claim)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if result:
                if isinstance(result, list):
                    evidence_list.extend(result)
                else:
                    evidence_list.append(result)

        # ---- LIMITED SEARCH FALLBACK ----
        start = time.time()
        print("Dynamic data:", time.time() - start)

        print("Search results:", time.time() - start)
        search_results = self.search_engine.search(claim)[:3]

        for result in search_results:
            url = result["url"]

            if exclude_domain and exclude_domain in url:
                continue

            content = self.scraper.scrape(url)

            if not content:
                continue

            evidence_list.append({
                "source": result["title"],
                "url": url,
                "text": content,
                "weight": get_weight(url)
            })

        return evidence_list
