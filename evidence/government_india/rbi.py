import requests


class RBIAPI:

    TOPIC_HINTS = {
        "inflation": "inflation statistics",
        "repo": "repo rate and monetary policy data",
        "interest": "interest rate statistics",
        "forex": "foreign exchange statistics",
        "currency": "currency and note issue data",
        "exchange rate": "exchange rate data",
    }

    def fetch(self, claim):

        claim_lower = (claim or "").lower()
        topic = None
        for word, label in self.TOPIC_HINTS.items():
            if word in claim_lower:
                topic = label
                break

        if topic is None:
            return None

        try:
            url = "https://dbie.rbi.org.in/DBIE/dbie.rbi?site=statistics"
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                return None

            return {
                "source": "Reserve Bank of India",
                "url": "https://www.rbi.org.in/",
                "text": f"RBI provides official {topic} through its DBIE statistics and monetary policy resources.",
                "weight": 0.92
            }

        except Exception as e:
            print("RBI API error:", e)
            return None
