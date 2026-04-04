import unittest
from unittest.mock import patch

from ingestion.ocr import choose_best_ocr_result, score_ocr_candidate


class OCRHelpersTest(unittest.TestCase):

    def test_score_ocr_candidate_rewards_position_weight(self):
        candidate = {
            "avg_confidence": 60.0,
            "word_count": 10,
            "script_ratio": 0.0,
        }
        base_score = score_ocr_candidate(candidate, position_weight=0.0)
        boosted_score = score_ocr_candidate(candidate, position_weight=1.25)
        self.assertAlmostEqual(boosted_score - base_score, 1.25)

    def test_choose_best_ocr_result_prefers_usable_text(self):
        variant_results = [
            {"text": "aa bb cc", "avg_confidence": 97.0, "word_count": 3},
            {
                "text": "Heavy rainfall likely across coastal districts tomorrow morning",
                "avg_confidence": 84.0,
                "word_count": 8,
            },
        ]

        with patch("ingestion.ocr.ocr_variant", side_effect=variant_results):
            best = choose_best_ocr_result(
                image_bgr="unused",
                lang="eng",
                config="--oem 3 --psm 6",
                variant_images=["variant1", "variant2"],
            )

        self.assertIsNotNone(best)
        self.assertTrue(best["usable"])
        self.assertEqual(
            best["text"],
            "Heavy rainfall likely across coastal districts tomorrow morning",
        )


if __name__ == "__main__":
    unittest.main()
