import requests
import re


class WHOAPI:

    BASE_URL = "https://ghoapi.azureedge.net/api"

    def extract_year(self, claim):
        match = re.search(r"\b(19|20)\d{2}\b", claim)
        return match.group(0) if match else None

    def fetch(self, claim):

        claim_lower = claim.lower()
        year = self.extract_year(claim)

        # Very basic topic routing
        if any(word in claim_lower for word in [
            "life expectancy",
            "mortality",
            "vaccination",
            "disease",
            "health"
        ]):

            try:
                # Example: Life expectancy indicator
                url = f"{self.BASE_URL}/IndicatorData"

                params = {
                    "$top": 5
                }

                response = requests.get(url, params=params, timeout=10)

                if response.status_code != 200:
                    return None

                return {
                    "source": "World Health Organization",
                    "url": "https://www.who.int/",
                    "text": f"WHO global health data available for health indicators in {year}.",
                    "weight": 0.95
                }

            except:
                return None

        return None
