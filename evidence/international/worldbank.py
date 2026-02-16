# evidence/international/worldbank.py

import requests

class WorldBankAPI:
    BASE_URL = "https://api.worldbank.org/v2"

    def get_gdp_data(self, country_code="IND", year="2024"):
        url = f"{self.BASE_URL}/country/{country_code}/indicator/NY.GDP.MKTP.CD"

        params = {
            "date": year,
            "format": "json"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if len(data) > 1 and data[1]:
                gdp_value = data[1][0]["value"]

                return {
                    "source": "World Bank",
                    "url": "https://data.worldbank.org/",
                    "text": f"India GDP in {year} was {gdp_value} USD according to World Bank.",
                    "weight": 0.95
                }

        except:
            return None

        return None
