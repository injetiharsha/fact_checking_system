import requests
import re
import pycountry


class WorldBankAPI:

    BASE_URL = "https://api.worldbank.org/v2"

    # Keyword → World Bank Indicator mapping
    INDICATOR_MAP = {
        "gdp": "NY.GDP.MKTP.CD",
        "gross domestic product": "NY.GDP.MKTP.CD",
        "economy": "NY.GDP.MKTP.CD",
        "largest economy": "NY.GDP.MKTP.CD",
        "population": "SP.POP.TOTL",
        "inflation": "FP.CPI.TOTL.ZG",
        "unemployment": "SL.UEM.TOTL.ZS",
        "life expectancy": "SP.DYN.LE00.IN",
        "poverty": "SI.POV.DDAY",
        "exports": "NE.EXP.GNFS.CD",
        "imports": "NE.IMP.GNFS.CD",
        "literacy": "SE.ADT.LITR.ZS"
    }

    COUNTRY_ALIASES = {
        "india": "IND",
        "indian": "IND",
        "united states": "USA",
        "usa": "USA",
        "us": "USA",
        "uk": "GBR",
        "united kingdom": "GBR",
    }

    def extract_year(self, claim):
        match = re.search(r"\b(19|20)\d{2}\b", claim)
        return match.group(0) if match else None

    def extract_country_code(self, claim):
        claim_lower = (claim or "").lower()
        for alias, code in self.COUNTRY_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", claim_lower):
                return code
        for country in pycountry.countries:
            if country.name.lower() in claim_lower:
                return country.alpha_3
        return None

    def detect_indicator(self, claim):
        claim_lower = claim.lower()
        ordered = sorted(self.INDICATOR_MAP.items(), key=lambda item: len(item[0]), reverse=True)
        for keyword, indicator in ordered:
            if keyword in claim_lower:
                return indicator, keyword
        return None, None

    def _format_value(self, value):
        if isinstance(value, float):
            return f"{value:,.2f}"
        if isinstance(value, int):
            return f"{value:,}"
        return str(value)

    def _country_label(self, country_code):
        try:
            country = pycountry.countries.get(alpha_3=country_code)
            return country.name if country else country_code
        except Exception:
            return country_code

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

            row = data[1][0]
            value = row["value"]

            if value is None:
                return None

            year_label = row.get("date") or year or "latest available year"
            country_label = self._country_label(country)
            value_label = self._format_value(value)

            return {
                "source": "World Bank",
                "url": "https://data.worldbank.org/",
                "text": f"World Bank reports that {country_label}'s {keyword} in {year_label} was {value_label}.",
                "weight": 0.95
            }

        except Exception as e:
            print("World Bank API error:", e)
            return None
