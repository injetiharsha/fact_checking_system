"""Tests for RBI evidence helper."""

import unittest
from unittest.mock import MagicMock, patch

from evidence.government_india.rbi import RBIAPI


class TestRBIEvidence(unittest.TestCase):
    @patch("evidence.government_india.rbi.requests.get")
    def test_returns_none_when_page_text_too_short(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "x" * 40
        resp.url = "https://data.rbi.org.in/test"
        mock_get.return_value = resp

        self.assertIsNone(RBIAPI().fetch("RBI inflation statistics"))

    @patch("evidence.government_india.rbi.requests.get")
    def test_returns_evidence_when_page_substantial(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "<html><body>" + ("word " * 50) + "</body></html>"
        resp.url = "https://data.rbi.org.in/ok"
        mock_get.return_value = resp

        out = RBIAPI().fetch("current inflation rate")
        self.assertIsNotNone(out)
        self.assertEqual(out["source"], "Reserve Bank of India")
        self.assertEqual(out["url"], "https://data.rbi.org.in/ok")
        self.assertIn("Page text excerpt", out["text"])
        self.assertIn("inflation", out["text"].lower())

    def test_no_topic_returns_none(self):
        self.assertIsNone(RBIAPI().fetch("random unrelated text xyz"))


if __name__ == "__main__":
    unittest.main()
