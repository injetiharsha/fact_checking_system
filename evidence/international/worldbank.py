import requests
import re
import pycountry


class WorldBankAPI:

    BASE_URL = "https://api.worldbank.org/v2"

    # Keyword → World Bank Indicator mapping
    INDICATOR_MAP = {
        "gdp": "NY.GDP.MKTP.CD",
        "population": "SP.POP.TOTL",
        "inflation": "FP.CPI.TOTL.ZG",
        "unemployment": "SL.UEM.TOTL.ZS",
        "life expectancy": "SP.DYN.LE00.IN",
        "poverty": "SI.POV.DDAY",
        "exports": "NE.EXP.GNFS.CD",
        "imports": "NE.IMP.GNFS.CD",
        "literacy": "SE.ADT.LITR.ZS"
    }

    def extract_year(self, claim):
        match = re.search(r"\b(19|20)\d{2}\b", claim)
        return match.group(0) if match else None

    def extract_country_code(self, claim):
        for country in pycountry.countries:
            if country.name.lower() in claim.lower():
                return country.alpha_3
        return None

    def detect_indicator(self, claim):
        claim_lower = claim.lower()
        for keyword, indicator in self.INDICATOR_MAP.items():
            if keyword in claim_lower:
                return indicator, keyword
        return None, None

    def fetch(self, claim):

        country = self.extract_country_code(claim)
        year = self.extract_year(claim)
        indicator, keyword = self.detect_indicator(claim)

        if not country or not indicator:
            return None

        try:
            url = f"{self.BASE_URL}/country/{country}/indicator/{indicator}"

            params = {
                "date": year if year else "",
                "format": "json"
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                return None

            data = response.json()

            if len(data) < 2 or not data[1]:
                return None

            value = data[1][0]["value"]

            if value is None:
                return None

            return {
                "source": "World Bank",
                "url": "https://data.worldbank.org/",
                "text": f"World Bank reports that {country} {keyword} in {year if year else 'latest available year'} was {value}.",
                "weight": 0.95
            }

        except Exception as e:
            print("World Bank API error:", e)
            return None
