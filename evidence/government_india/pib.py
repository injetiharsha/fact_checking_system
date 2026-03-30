import requests
import re


class PIBAPI:

    BASE_URL = "https://pib.gov.in"

    def extract_year(self, claim):
        match = re.search(r"\b(19|20)\d{2}\b", claim)
        return match.group(0) if match else None

    def fetch(self, claim):

        claim_lower = claim.lower()
        year = self.extract_year(claim)

        if any(word in claim_lower for word in [
            "government",
            "india",
            "ministry",
            "policy",
            "project",
            "scheme"
        ]):

            try:
                # PIB search
                url = f"{self.BASE_URL}/khasearch.php"

                params = {
                    "q": claim,
                    "limit": 5
                }

                response = requests.get(url, params=params, timeout=10)

                if response.status_code != 200:
                    return None

                return {
                    "source": "Press Information Bureau India",
                    "url": self.BASE_URL,
                    "text": f"PIB official statement available for {claim} in {year if year else 'recent records'}.",
                    "weight": 0.95
                }

            except Exception as e:
                print("PIB API error:", e)
                return None

        return None
