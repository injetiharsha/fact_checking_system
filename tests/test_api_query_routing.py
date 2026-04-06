import unittest

from evidence.government_india.rbi import RBIAPI
from evidence.international.worldbank import WorldBankAPI
from evidence.international.who import WHOAPI
from evidence.router import EvidenceRouter


class APIQueryRoutingTest(unittest.TestCase):

    def test_worldbank_recognizes_common_country_alias(self):
        api = WorldBankAPI()
        self.assertEqual(api.extract_country_code("India GDP in 2024"), "IND")

    def test_rbi_uses_topic_specific_context(self):
        api = RBIAPI()
        api.fetch = RBIAPI.fetch.__get__(api, RBIAPI)

        class _Response:
            status_code = 200

        import evidence.government_india.rbi as rbi_mod

        original_get = rbi_mod.requests.get
        rbi_mod.requests.get = lambda *args, **kwargs: _Response()
        try:
            row = api.fetch("India inflation rate")
        finally:
            rbi_mod.requests.get = original_get

        self.assertIsNotNone(row)
        self.assertIn("inflation statistics", row["text"])

    def test_who_triggers_for_covid_wording(self):
        api = WHOAPI()

        class _Response:
            status_code = 200

        import evidence.international.who as who_mod

        original_get = who_mod.requests.get
        who_mod.requests.get = lambda *args, **kwargs: _Response()
        try:
            row = api.fetch("5G network spreads COVID virus")
        finally:
            who_mod.requests.get = original_get

        self.assertIsNotNone(row)
        self.assertIn("COVID-19", row["text"])

    def test_worldbank_maps_largest_economy_to_gdp(self):
        api = WorldBankAPI()
        indicator, keyword = api.detect_indicator("India is the 4th largest economy in 2026")
        self.assertEqual(indicator, "NY.GDP.MKTP.CD")
        self.assertEqual(keyword, "largest economy")

    def test_router_builds_rank_and_fact_check_query_rewrites(self):
        router = object.__new__(EvidenceRouter)
        economy_queries = router._build_search_queries(
            "India is the 4th largest economy in 2026",
            context_result={"domain": "economics_business"},
            claim_type_result={"type": "factual"},
        )
        self.assertTrue(any("nominal gdp ranking" in query.lower() for query in economy_queries))
        self.assertTrue(any("imf world economic outlook" in query.lower() for query in economy_queries))

        health_queries = router._build_search_queries(
            "5G network spreads COVID virus",
            context_result={"domain": "health"},
            claim_type_result={"type": "factual"},
        )
        self.assertTrue(any("fact check" in query.lower() for query in health_queries))


if __name__ == "__main__":
    unittest.main()
