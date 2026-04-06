import asyncio
import unittest
from unittest.mock import patch

from pipeline.document_pipeline import DocumentPipeline


class _StubClaimTypeClassifier:
    def classify(self, text):
        lowered = text.lower()
        if "breaking" in lowered:
            return {"type": "mixed"}
        if any(token in lowered for token in (" is ", " are ", " was ", " has ", " 2024 ")):
            return {"type": "factual"}
        return {"type": "opinion"}


class _StubLogicalAnalyzer:
    def analyze(self, text):
        lowered = text.lower()
        return {
            "has_numeric_value": any(ch.isdigit() for ch in text),
            "is_opinion": "best" in lowered or "amazing" in lowered,
        }


class _StubClaimCheckability:
    def classify(self, text, claim_type_result=None, logical_metadata=None):
        lowered = text.lower()
        allowed = "breaking news" not in lowered and not logical_metadata.get("is_opinion")
        return {
            "allowed": allowed,
            "confidence": 0.9 if allowed else 0.9,
            "code": "checkable" if allowed else "not_checkable_other",
        }


class _StubExtractor:
    def extract_claims(self, text):
        return [part.strip() for part in (text or "").split(".") if part.strip()]

    def extract_main_claim(self, text):
        return "fallback claim"


class _StubRelevanceScorer:
    def semantic_score(self, document_text, text):
        text_lower = " ".join(text.lower().split())
        if text_lower == "hyderabad is the capital of telangana":
            return 0.95
        if text_lower == "a delivery agent fell from a moving train near anantapur railway station":
            return 0.94
        if text_lower == "a shocking incident has come to light":
            return 0.2
        if text_lower == "share this update with friends":
            return 0.05
        return 0.4


class DocumentPipelineSelectorTest(unittest.TestCase):

    def _build_pipeline(self):
        pipeline = object.__new__(DocumentPipeline)
        pipeline.extractor = _StubExtractor()
        pipeline.claim_pipeline = type(
            "StubClaimPipeline",
            (),
            {
                "claim_type_classifier": _StubClaimTypeClassifier(),
                "logical_analyzer": _StubLogicalAnalyzer(),
                "claim_checkability": _StubClaimCheckability(),
                "relevance_scorer": _StubRelevanceScorer(),
            },
        )()
        return pipeline

    def test_prefers_checkable_claim_over_noisy_heading(self):
        pipeline = self._build_pipeline()
        text = (
            "BREAKING NEWS\n"
            "share this update with friends\n"
            "Hyderabad is the capital of Telangana.\n"
            "Read more on our channel."
        )

        selection = pipeline._select_image_main_claim(text)

        self.assertEqual(selection["claim"], "Hyderabad is the capital of Telangana")
        self.assertEqual(selection["reason"], "existing_model_selector")
        self.assertTrue(selection["candidates"])

    def test_image_clean_paragraph_uses_fast_path(self):
        pipeline = self._build_pipeline()
        pipeline.extractor = type(
            "FastPathExtractor",
            (),
            {
                "extract_main_claim": lambda _self, text: "India's GDP grew by 7.8 percent in FY2024",
            },
        )()

        def _fail_if_heavy_path(*_args, **_kwargs):
            raise AssertionError("heavy candidate scoring should be skipped for clean OCR paragraph")

        pipeline._model_score_image_candidate = _fail_if_heavy_path
        text = (
            "India's GDP grew by 7.8 percent in FY2024 according to provisional estimates. "
            "The report notes stronger manufacturing and services output over the previous year."
        )

        selection = pipeline._select_image_main_claim(text)

        self.assertEqual(selection["reason"], "ocr_clean_text_fast_path")
        self.assertEqual(selection["claim"], "India's GDP grew by 7.8 percent in FY2024")
        self.assertEqual(selection["candidates"], [])

    def test_synthesizes_claim_from_block_and_skips_shell_sentence(self):
        pipeline = self._build_pipeline()
        block = (
            "A shocking incident has come to light. "
            "A delivery agent fell from a moving train near Anantapur railway station."
        )

        claim = pipeline._synthesize_claim_from_block(block)

        self.assertEqual(
            claim,
            "A delivery agent fell from a moving train near Anantapur railway station",
        )

    def test_process_image_forwards_ocr_text_as_source_text(self):
        pipeline = object.__new__(DocumentPipeline)
        test_case = self
        captured = {}

        async def fake_run(_self, claim, source_url=None, source_text=None, allow_llm_verifier=None):
            captured["claim"] = claim
            captured["source_text"] = source_text
            test_case.assertEqual(claim, "selected claim")
            test_case.assertEqual(source_text, "OCR text body")
            return {
                "results": [{"final_verdict": "TRUE"}],
                "document_verdict": "Highly Reliable",
                "ocr_details": {"selected_claim": "selected claim"},
            }

        pipeline.claim_pipeline = type("StubClaimPipeline", (), {"run": fake_run})()
        pipeline._select_image_main_claim = lambda text: {
            "claim": "selected claim",
            "reason": "existing_model_selector",
            "score": 0.9,
            "candidates": [],
        }

        with patch("pipeline.document_pipeline.extract_image_text", return_value={
            "text": "OCR text body",
            "usable": True,
            "reason": "ok",
            "avg_confidence": 0.99,
        }):
            asyncio.run(pipeline.process_image("dummy.png"))

        self.assertEqual(captured["claim"], "selected claim")
        self.assertEqual(captured["source_text"], "OCR text body")

    def test_process_pdf_analyzes_each_page(self):
        pipeline = object.__new__(DocumentPipeline)
        pipeline.extractor = _StubExtractor()
        pipeline.claim_pipeline = type(
            "StubClaimPipeline",
            (),
            {
                "claim_type_classifier": _StubClaimTypeClassifier(),
                "logical_analyzer": _StubLogicalAnalyzer(),
                "claim_checkability": _StubClaimCheckability(),
                "relevance_scorer": _StubRelevanceScorer(),
            },
        )()
        seen_pages = []
        seen_source_text = []

        async def fake_process_text(text, source_url=None, ocr_details=None, selected_claim=None, source_text=None, allow_llm_verifier=True):
            seen_pages.append(text)
            seen_source_text.append(source_text)
            return {
                "final_verdict": "TRUE" if "page one" in text.lower() else "FALSE",
                "confidence": 1.0,
                "results": [],
            }

        pipeline._process_text = fake_process_text

        with patch("pipeline.document_pipeline.extract_pdf_with_details", return_value={
            "text": "Page one claim\nPage two claim",
            "pages": [
                {"page_number": 1, "text": "Page one claim", "source": "pdfplumber"},
                {"page_number": 2, "text": "Page two claim", "source": "pdfplumber"},
            ],
            "ocr_details": None,
            "extraction_source": "pdfplumber",
        }):
            result = asyncio.run(pipeline.process_pdf("dummy.pdf"))

        self.assertEqual(seen_pages, ["Page one claim", "Page two claim"])
        self.assertIn("Page one claim", seen_source_text[0])
        self.assertIn("Page two claim", seen_source_text[0])
        self.assertEqual(result["pages_analyzed"], 2)
        self.assertEqual(result["claims_analyzed"], 2)
        self.assertEqual(len(result["results"]), 2)
        self.assertTrue(result.get("section_overview"))

    def test_select_text_main_claim_uses_page_context(self):
        pipeline = self._build_pipeline()
        text = (
            "Introduction and overview. "
            "This page summarizes background context. "
            "Hyderabad is the capital of Telangana."
        )

        selection = pipeline._select_text_main_claim(text)

        self.assertEqual(selection["claim"], "Hyderabad is the capital of Telangana")
        self.assertEqual(selection["reason"], "page_context_selector")
        self.assertTrue(selection["candidates"])

    def test_select_text_main_claim_fast_path_when_enabled(self):
        pipeline = self._build_pipeline()
        pipeline.extractor = type(
            "FastPathExtractor",
            (),
            {
                "extract_main_claim": lambda _self, text: "Rainfall may increase in coastal districts over the next 24 hours",
            },
        )()

        def _fail_if_heavy_path(*_args, **_kwargs):
            raise AssertionError("heavy candidate scoring should be skipped for clean OCR paragraph")

        pipeline._model_score_image_candidate = _fail_if_heavy_path
        text = (
            "Rainfall may increase in coastal districts over the next 24 hours according to the latest weather bulletin. "
            "Officials advised residents in low-lying areas to stay alert and follow local warnings."
        )

        selection = pipeline._select_text_main_claim(text, prefer_fast_path=True)

        self.assertEqual(selection["reason"], "ocr_clean_text_fast_path")
        self.assertEqual(
            selection["claim"],
            "Rainfall may increase in coastal districts over the next 24 hours",
        )
        self.assertEqual(selection["candidates"], [])

    def test_select_text_main_claim_uses_heading_alignment_bonus(self):
        pipeline = self._build_pipeline()
        candidates = [
            "Hospital admissions increased in several districts",
            "Environmental impact reached dangerous levels in three zones",
        ]
        pipeline.extractor = type(
            "HeadingAwareExtractor",
            (),
            {
                "extract_claims": lambda _self, _text: candidates,
                "extract_main_claim": lambda _self, _text: candidates[0],
            },
        )()

        def _scorer(_doc_text, candidate_text):
            base = 0.55
            if "hospital admissions" in candidate_text.lower():
                base = 0.56
            return {
                "text": candidate_text,
                "score": base,
                "checkable": True,
            }

        pipeline._model_score_image_candidate = _scorer
        text = (
            "Environmental Impact\n"
            "This section summarizes impacts observed during the monitoring period."
        )

        selection = pipeline._select_text_main_claim(text)

        self.assertEqual(
            selection["claim"],
            "Environmental impact reached dangerous levels in three zones",
        )
        best_candidate = selection["candidates"][0]
        self.assertGreater(best_candidate.get("heading_bonus", 0.0), 0.0)

    def test_should_use_pdf_fast_path_allows_text_layer_when_well_formed(self):
        pipeline = self._build_pipeline()

        image_page = {
            "text": "Emergency alert for coastal districts. Heavy rain is expected in the next 24 hours and local officials asked residents to avoid low-lying routes.",
            "source": "pdfplumber",
            "image_count": 1,
            "word_count": 24,
            "text_chars": 148,
        }
        short_text_page = {
            "text": "District bulletin says high winds may continue through evening and schools should remain closed until official clearance is issued.",
            "source": "pdfplumber",
            "image_count": 0,
            "word_count": 19,
            "text_chars": 126,
        }
        long_text_page = {
            "text": " ".join(["policy"] * 120),
            "source": "pdfplumber",
            "image_count": 0,
            "word_count": 120,
            "text_chars": 840,
        }
        noisy_text_page = {
            "text": " ".join(["token"] * 600),
            "source": "pdfplumber",
            "image_count": 0,
            "word_count": 600,
            "text_chars": 3600,
        }

        self.assertTrue(pipeline._should_use_pdf_fast_path(image_page))
        self.assertTrue(pipeline._should_use_pdf_fast_path(short_text_page))
        self.assertFalse(pipeline._should_use_pdf_fast_path(long_text_page))
        self.assertFalse(pipeline._should_use_pdf_fast_path(noisy_text_page))

    def test_should_use_pdf_fast_path_section_heading_blocks_fast_path(self):
        pipeline = self._build_pipeline()
        page = {
            "text": "District bulletin warns of gusty winds in low-lying areas and asks residents to stay indoors.",
            "source": "pdfplumber",
            "section_topic": "References",
            "word_count": 15,
            "text_chars": 96,
        }

        self.assertFalse(pipeline._should_use_pdf_fast_path(page))

    def test_should_use_pdf_fast_path_section_heading_prefer_relaxes_limits(self):
        pipeline = self._build_pipeline()
        page = {
            "text": " ".join(["update"] * 80) + ".",
            "source": "pdfplumber",
            "section_topic": "Executive Summary",
            "word_count": 80,
            "text_chars": 560,
        }

        self.assertTrue(pipeline._should_use_pdf_fast_path(page))

    def test_build_section_summary_uses_heading_and_claim(self):
        pipeline = self._build_pipeline()
        page_text = "Environmental Management Plan\nEarly Warning Systems\nDetails..."
        selected_claim = "Bangladesh has since invested in early-warning systems"

        summary = pipeline._build_section_summary(page_text, selected_claim)

        self.assertIn("Environmental Management Plan", summary)
        self.assertIn("Bangladesh has since invested in early-warning systems", summary)

    def test_assign_sections_to_pages_carries_forward_topic(self):
        pipeline = self._build_pipeline()
        pages = [
            {"page_number": 1, "text": "Environmental Management Plan\nPage one"},
            {"page_number": 2, "text": "Page two without heading"},
        ]

        assigned = pipeline._assign_sections_to_pages(pages)

        self.assertEqual(assigned[0]["section_topic"], "Environmental Management Plan")
        self.assertEqual(assigned[1]["section_topic"], "Environmental Management Plan")

    def test_generate_context_summary_extractive(self):
        pipeline = self._build_pipeline()
        text = (
            "The Bhola cyclone caused severe flooding and major loss of life. "
            "The report documents impacts on water, soil, and agriculture. "
            "It also describes mitigation and early warning systems."
        )

        summary = pipeline._generate_context_summary(text, topic="Environmental Impact Assessment")

        self.assertTrue(summary)
        self.assertLessEqual(len(summary), 280)


if __name__ == "__main__":
    unittest.main()
