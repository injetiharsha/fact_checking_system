from evidence.international.worldbank import WorldBankAPI
from evidence.international.un_data import UNDataAPI
from evidence.government_india.national_router import NationalDataRouter


class DynamicDataRouter:

    def __init__(self, data_gov_key=None):
        self.worldbank = WorldBankAPI()

        self.un = UNDataAPI()
        self.national = NationalDataRouter(data_gov_key)

    def fetch(self, claim):

        # 🇮🇳 National first
        national = self.national.fetch(claim)
        if national:
            return national

        # 🌍 Global
        wb = self.worldbank.fetch(claim)
        if wb:
            return wb

        un = self.un.fetch(claim)
        if un:
            return un

        return None
