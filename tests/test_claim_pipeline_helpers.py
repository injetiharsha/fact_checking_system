"""Unit tests for claim_pipeline numeric / claim-type helpers."""

import unittest
from enum import Enum

from pipeline.claim_type_utils import (
    best_numeric_pairwise_rel_diff,
    claim_type_label_lower,
    collect_non_year_numeric_values,
)


class _DummyClaimType(Enum):
    FACTUAL = "factual"
    NUMERICAL = "numerical"
    OPINION = "opinion"


class TestClaimTypeUtils(unittest.TestCase):
    def test_claim_type_label_lower_enum(self):
        self.assertEqual(claim_type_label_lower({"type": _DummyClaimType.FACTUAL}), "factual")
        self.assertEqual(claim_type_label_lower({"type": _DummyClaimType.NUMERICAL}), "numerical")
        self.assertEqual(claim_type_label_lower({"type": _DummyClaimType.OPINION}), "opinion")

    def test_claim_type_label_lower_string(self):
        self.assertEqual(claim_type_label_lower({"type": "factual"}), "factual")

    def test_claim_type_label_lower_empty(self):
        self.assertEqual(claim_type_label_lower({}), "")

    def test_collect_non_year_includes_small_magnitudes(self):
        vals = collect_non_year_numeric_values(["0.05", "0.051"])
        self.assertIn(0.05, vals)
        self.assertIn(0.051, vals)

    def test_collect_non_year_skips_years(self):
        vals = collect_non_year_numeric_values(["1999", "3.14"])
        self.assertNotIn(1999, vals)
        self.assertIn(3.14, vals)

    def test_best_numeric_pairwise_symmetric(self):
        rd = best_numeric_pairwise_rel_diff([0.05, 500.0], [0.051, 10.0])
        self.assertIsNotNone(rd)
        self.assertLessEqual(rd, 0.02)

    def test_best_numeric_pairwise_none_when_empty(self):
        self.assertIsNone(best_numeric_pairwise_rel_diff([], [1.0]))
        self.assertIsNone(best_numeric_pairwise_rel_diff([1.0], []))


if __name__ == "__main__":
    unittest.main()
