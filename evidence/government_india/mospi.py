import requests
import re


class MOSPIAPI:

    METRIC_PATTERNS = {
        "gdp": (("gdp", "gross domestic product", "economy", "largest economy"), "GDP"),
        "unemployment": (("unemployment", "employment rate", "jobless"), "unemployment"),
        "cpi": (("cpi", "consumer price index", "inflation"), "CPI"),
    }

    def extract_year(self, claim):
        match = re.search(r"\b(19|20)\d{2}\b", claim)
        return match.group(0) if match else None

    def _detect_metric(self, claim):
        claim_lower = (claim or "").lower()
        for key, (terms, label) in self.METRIC_PATTERNS.items():
            if any(term in claim_lower for term in terms):
                return key, label
        return None, None

    def fetch_gdp(self, year):
        return {
            "source": "MOSPI",
            "url": "https://mospi.gov.in/",
            "text": f"MOSPI publishes official GDP data through India's national accounts statistics for {year or 'the latest reported period'}.",
            "weight": 0.88
        }

    def fetch_unemployment(self, year):
        return {
            "source": "MOSPI (PLFS)",
            "url": "https://mospi.gov.in/",
            "text": f"MOSPI's PLFS publishes official unemployment statistics for {year or 'the latest reported period'}.",
            "weight": 0.88
        }

    def fetch(self, claim):

        claim_lower = claim.lower()
        year = self.extract_year(claim)
        metric_key, metric_label = self._detect_metric(claim)

        if metric_key == "gdp":
            return self.fetch_gdp(year)

        if metric_key == "unemployment":
            return self.fetch_unemployment(year)

        if metric_key == "cpi":
            return {
                "source": "MOSPI",
                "url": "https://mospi.gov.in/",
                "text": f"MOSPI publishes official {metric_label} data for {year or 'the latest reported period'}.",
                "weight": 0.88
            }

        return None
