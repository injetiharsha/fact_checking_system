import requests
import re


class MOSPIAPI:

    def extract_year(self, claim):
        match = re.search(r"\b(19|20)\d{2}\b", claim)
        return match.group(0) if match else None

    def fetch_gdp(self, year):
        return {
            "source": "MOSPI",
            "url": "https://mospi.gov.in/",
            "text": f"MOSPI publishes official GDP data for {year}.",
            "weight": 1.0
        }

    def fetch_unemployment(self, year):
        return {
            "source": "MOSPI (PLFS)",
            "url": "https://mospi.gov.in/",
            "text": f"PLFS unemployment data for {year} available via MOSPI.",
            "weight": 1.0
        }

    def fetch(self, claim):

        claim_lower = claim.lower()
        year = self.extract_year(claim)

        if "gdp" in claim_lower:
            return self.fetch_gdp(year)

        if "unemployment" in claim_lower or "employment rate" in claim_lower:
            return self.fetch_unemployment(year)

        if "cpi" in claim_lower:
            return {
                "source": "MOSPI",
                "url": "https://mospi.gov.in/",
                "text": "Official CPI data published by MOSPI.",
                "weight": 1.0
            }

        return None
