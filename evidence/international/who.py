import requests
import re


class WHOAPI:

    BASE_URL = "https://ghoapi.azureedge.net/api"
    HEALTH_MARKERS = {
        "life expectancy",
        "mortality",
        "vaccination",
        "disease",
        "health",
        "covid",
        "virus",
        "public health",
        "infection",
        "infectious",
    }
    TOPIC_HINTS = (
        ("covid", "COVID-19"),
        ("vaccine", "vaccination"),
        ("mortality", "mortality"),
        ("life expectancy", "life expectancy"),
        ("virus", "infectious disease"),
        ("disease", "disease"),
        ("health", "health"),
    )

    def extract_year(self, claim):
        match = re.search(r"\b(19|20)\d{2}\b", claim)
        return match.group(0) if match else None

    def fetch(self, claim):

        claim_lower = claim.lower()
        year = self.extract_year(claim)

        if any(word in claim_lower for word in self.HEALTH_MARKERS):

            try:
                url = f"{self.BASE_URL}/Indicator"

                params = {
                    "$top": 5
                }

                response = requests.get(url, params=params, timeout=10)

                if response.status_code != 200:
                    return None

                topic = self._topic_hint(claim_lower)

                return {
                    "source": "World Health Organization",
                    "url": "https://www.who.int/",
                    "text": f"WHO maintains official global health indicators relevant to {topic} for {year or 'recent reporting periods'}.",
                    "weight": 0.95
                }

            except:
                return None

        return None

    def _topic_hint(self, claim_lower):
        for marker, label in self.TOPIC_HINTS:
            if marker in claim_lower:
                return label
        return "public health"
