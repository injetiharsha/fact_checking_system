import requests


class RBIAPI:

    def fetch(self, claim):

        if not any(word in claim.lower() for word in ["inflation", "repo", "interest", "forex"]):
            return None

        try:
            url = "https://dbie.rbi.org.in/DBIE/dbie.rbi?site=statistics"
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                return None

            return {
                "source": "Reserve Bank of India",
                "url": "https://www.rbi.org.in/",
                "text": "RBI provides official financial statistics and monetary policy data.",
                "weight": 1.0
            }

        except Exception as e:
            print("RBI API error:", e)
            return None
