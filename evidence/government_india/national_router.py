
from evidence.government_india.rbi import RBIAPI


class NationalDataRouter:

    def __init__(self, api_key):
        
        self.rbi = RBIAPI()

    def fetch(self, claim):

        

        # 2️⃣ RBI financial
        rbi = self.rbi.fetch(claim)
        if rbi:
            return rbi

        return None
