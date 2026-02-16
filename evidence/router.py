# evidence/router.py

from urllib.parse import urlparse
from evidence.international.worldbank import WorldBankAPI
from evidence.general_search import SearchEngine
from evidence.scraper import WebScraper
from evidence.credibility_weights import get_weight


class EvidenceRouter:
    def __init__(self):
        self.search_engine = SearchEngine()
        self.scraper = WebScraper()
        self.worldbank = WorldBankAPI()

    def _get_domain(self, url):
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")

    def get_evidence(self, claim, exclude_domain=None):
        evidence_list = []

        # ✅ World Bank structured data (no domain filtering needed)
        if "economy" in claim.lower() or "gdp" in claim.lower():
            wb_data = self.worldbank.get_gdp_data("IND", "2024")

            if wb_data:
                evidence_list.append(wb_data)

        # 🔎 Web search
        search_results = self.search_engine.search(claim)

        for result in search_results:
            result_domain = self._get_domain(result["url"])

            # 🔥 Prevent self-verification
            if exclude_domain and exclude_domain == result_domain:
                continue

            content = self.scraper.scrape(result["url"])

            if content:
                evidence_list.append({
                    "source": result["title"],
                    "url": result["url"],
                    "text": content,
                    "weight": get_weight(result["url"])
                })

        return evidence_list
