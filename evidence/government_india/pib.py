from evidence.international.worldbank import WorldBankAPI
from evidence.general_search import SearchEngine
from evidence.scraper import WebScraper
from evidence.credibility_weights import get_weight
from evidence.relevance import RelevanceScorer
from evidence.quality import QualityScorer


class EvidenceRouter:

    def __init__(self):
        self.search_engine = SearchEngine()
        self.scraper = WebScraper()
        self.worldbank = WorldBankAPI()

        self.relevance = RelevanceScorer()
        self.quality = QualityScorer()

    def get_evidence(self, claim, exclude_domain=None):

        evidence_list = []

        # 1️⃣ Economic routing
        if "economy" in claim.lower() or "gdp" in claim.lower():

            wb_data = self.worldbank.get_gdp_data("IND", "2024")

            if wb_data:
                evidence_list.append(wb_data)

        # 2️⃣ General search fallback
        search_results = self.search_engine.search(claim)

        for result in search_results:

            url = result["url"]

            if exclude_domain and exclude_domain in url:
                continue

            content = self.scraper.scrape(url)

            if not content:
                continue

            relevance_score = self.relevance.score(claim, content)
            quality_score = self.quality.score(content)
            credibility_weight = get_weight(url)

            final_weight = round(
                relevance_score * quality_score * credibility_weight,
                3
            )

            evidence_list.append({
                "source": result["title"],
                "url": url,
                "text": content,
                "weight": final_weight
            })

        return evidence_list
