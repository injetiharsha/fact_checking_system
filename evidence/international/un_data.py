import requests
import re
import pycountry


class UNDataAPI:

    BASE_URL = "https://unstats.un.org/SDGAPI/v1/sdg/Indicator/Data"

    # Minimal topic → indicator mapping
    TOPIC_MAP = {
        "population": "1.1.1",
        "poverty": "1.2.1",
        "education": "4.1.1",
        "health": "3.1.1",
        "employment": "8.5.2"
    }

    def extract_year(self, claim):
        match = re.search(r"\b(19|20)\d{2}\b", claim)
        return match.group(0) if match else None

    def extract_country_code(self, claim):
        for country in pycountry.countries:
            if country.name.lower() in claim.lower():
                return country.alpha_3
        return None

    def detect_topic(self, claim):
        claim_lower = claim.lower()
        for keyword, indicator in self.TOPIC_MAP.items():
            if keyword in claim_lower:
                return indicator
        return None

    def fetch(self, claim):

        country = self.extract_country_code(claim)
        year = self.extract_year(claim)
        indicator = self.detect_topic(claim)

        if not country or not indicator:
            return None

        try:
            params = {
                "indicator": indicator,
                "areaCode": country
            }

            response = requests.get(self.BASE_URL, params=params, timeout=10)

            if response.status_code != 200:
                return None

            data = response.json()

            if not data:
                return None

            # Just return first record for now
            record = data[0]

            return {
                "source": "United Nations",
                "url": "https://unstats.un.org/",
                "text": f"UN reports indicator {indicator} for {country}: {record}",
                "weight": 0.95
            }

        except Exception as e:
            print("UN API error:", e)
            return None
