import requests
import re


class OECDAPI:

    BASE_URL = "https://stats.oecd.org/SDMX-JSON/data"
    ECONOMIC_MARKERS = {
        "employment",
        "unemployment",
        "productivity",
        "education",
        "gdp",
        "economy",
        "largest economy",
    }

    def extract_year(self, claim):
        match = re.search(r"\b(19|20)\d{2}\b", claim)
        return match.group(0) if match else None

    def fetch(self, claim):

        claim_lower = claim.lower()
        year = self.extract_year(claim)

        if any(word in claim_lower for word in self.ECONOMIC_MARKERS):

            try:
                # Example dataset call (simplified)
                url = f"{self.BASE_URL}/MEI"

                response = requests.get(url, timeout=10)

                if response.status_code != 200:
                    return None

                return {
                    "source": "OECD",
                    "url": "https://www.oecd.org/",
                    "text": f"OECD maintains structured economic data relevant to this claim for {year or 'recent reporting periods'}.",
                    "weight": 0.95
                }

            except:
                return None

        return None
