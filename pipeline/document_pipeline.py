import os
import re
import time
import asyncio

import requests

from ingestion.webpage import WebpageIngestor
from ingestion.pdf import extract_pdf_with_details
from ingestion.image import extract_image_text
from nlp.language import detect_language

from claim_detection.extractor import ClaimExtractor
from pipeline.claim_pipeline import ClaimPipeline
from verdict.document_scorer import score_document


class DocumentPipeline:

    def __init__(self):
        self.web_ingestor = WebpageIngestor()
        self.extractor = ClaimExtractor()
        self.claim_pipeline = ClaimPipeline()
        self.context_summary_mode = os.getenv("CONTEXT_SUMMARY_MODE", "extractive").strip().lower()
        self.context_summary_max_chars = max(120, int(os.getenv("CONTEXT_SUMMARY_MAX_CHARS", "280")))
        self.context_summary_max_sentences = max(1, int(os.getenv("CONTEXT_SUMMARY_MAX_SENTENCES", "2")))
        self.context_llm_enabled = os.getenv("ENABLE_LLM_CONTEXT_SUMMARIZER", "0").strip().lower() in {
            "1", "true", "yes", "on"
        }
        self.context_llm_api_key = (
            os.getenv("LLM_CONTEXT_API_KEY")
            or os.getenv("LLM_VERIFIER_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        self.context_llm_api_base = (
            os.getenv("LLM_CONTEXT_API_BASE")
            or os.getenv("LLM_VERIFIER_API_BASE")
            or os.getenv("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self.context_llm_model = (
            os.getenv("LLM_CONTEXT_MODEL")
            or os.getenv("LLM_VERIFIER_MODEL")
            or "gpt-4o-mini"
        )
        self.context_llm_timeout = float(os.getenv("LLM_CONTEXT_TIMEOUT_SECONDS", "30"))
        self.pdf_analysis_max_pages = self._safe_env_int("PDF_ANALYSIS_MAX_PAGES", 4)

    def _safe_env_int(self, name, default):
        try:
            return max(0, int(os.getenv(name, str(default)).strip()))
        except Exception:
            return default

    @staticmethod
    def _parse_page_range(page_range, total_pages):
        raw = str(page_range or "").strip()
        if not raw:
            return None
        match = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", raw)
        if not match:
            raise ValueError("Page selection must look like 1 or 1-2.")
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if start < 1 or end < 1 or end < start:
            raise ValueError("Invalid page selection.")
        if total_pages and start > total_pages:
            raise ValueError(f"Selected page {start} is outside this PDF.")
        if total_pages:
            end = min(end, total_pages)
        if (end - start + 1) > 5:
            raise ValueError("Select up to 5 pages at a time.")
        return start, end

    @staticmethod
    def _raise_if_cancelled(cancel_event=None):
        if cancel_event is not None and cancel_event.is_set():
            raise asyncio.CancelledError()

    @staticmethod
    def _emit_progress(progress_callback=None, **event):
        if progress_callback is None:
            return
        try:
            progress_callback(event)
        except Exception:
            return

    @staticmethod
    async def _flush_progress():
        await asyncio.sleep(0)

    @staticmethod
    def _infer_source_language(text, ocr_details=None):
        ocr_langs = str((ocr_details or {}).get("ocr_langs") or "").lower()
        language_map = (
            ("te", ("tel", "te")),
            ("ta", ("tam", "ta")),
            ("kn", ("kan", "kn")),
            ("ml", ("mal", "ml")),
            ("hi", ("hin", "hi")),
            ("bn", ("ben", "bn")),
            ("mr", ("mar", "mr")),
            ("gu", ("guj", "gu")),
            ("pa", ("pan", "pa")),
            ("ur", ("urd", "ur")),
            ("or", ("ori", "or")),
            ("as", ("asm", "as")),
        )
        for code, tokens in language_map:
            if any(token in ocr_langs for token in tokens):
                return code
        return detect_language(text)

    async def run(self, url):
        text = self.web_ingestor.extract_text(url)
        return await self._process_text(text, source_url=url, source_modality="web")

    async def process_pdf(self, file_path, page_range=None, cancel_event=None, progress_callback=None):
        total_start = time.time()
        self._emit_progress(progress_callback, stage="document_parse", status="active", detail="Extracting PDF text and page structure")
        await self._flush_progress()
        self._raise_if_cancelled(cancel_event)
        extract_start = time.time()
        pdf_result = await asyncio.to_thread(extract_pdf_with_details, file_path)
        print("PDF extract:", round(time.time() - extract_start, 3), "sec")
        self._raise_if_cancelled(cancel_event)
        text = (pdf_result or {}).get("text", "")
        pages = list((pdf_result or {}).get("pages") or [])
        total_pages_detected = len(pages)
        self._emit_progress(progress_callback, stage="document_parse", status="done", detail=f"Extracted {total_pages_detected or 1} page(s)")
        await self._flush_progress()
        ocr_details = (pdf_result or {}).get("ocr_details")
        source_language = self._infer_source_language(text, ocr_details)

        if not text:
            return {"error": "Could not extract text"}

        if ocr_details is not None and not ocr_details.get("usable", False):
            return {
                "error": "Could not reliably extract text from PDF",
                "ocr_details": {
                    "reason": ocr_details.get("reason"),
                    "avg_confidence": ocr_details.get("avg_confidence"),
                    "word_count": ocr_details.get("word_count"),
                    "script_ratio": ocr_details.get("script_ratio"),
                    "ocr_langs": ocr_details.get("ocr_langs"),
                    "ocr_pages_scanned": ocr_details.get("ocr_pages_scanned"),
                    "usable_page_count": ocr_details.get("usable_page_count"),
                    "text_preview": text[:240],
                },
            }

        if not pages:
            pages = [{
                "page_number": 1,
                "text": text,
                "source": (pdf_result or {}).get("extraction_source", "pdf"),
            }]

        selected_page_range = self._parse_page_range(page_range, total_pages_detected)
        if selected_page_range:
            start_page, end_page = selected_page_range
            pages = [
                page for page in pages
                if start_page <= int((page or {}).get("page_number") or 0) <= end_page
            ]
            if not pages:
                raise ValueError("No pages matched the selected page range.")

        if self.pdf_analysis_max_pages > 0:
            pages = pages[:self.pdf_analysis_max_pages]

        analysis_warning = None
        if total_pages_detected > 5:
            analysis_warning = (
                f"Time-intensive PDF detected ({total_pages_detected} pages). "
                f"Analyzing first {len(pages)} pages only."
            )
        if selected_page_range:
            selected_note = f"Selected pages {selected_page_range[0]}-{selected_page_range[1]}."
            analysis_warning = f"{selected_note} {analysis_warning}".strip() if analysis_warning else selected_note

        sectionized_pages = self._assign_sections_to_pages(pages)
        section_text_by_key = {}
        section_topic_by_key = {}
        for page in sectionized_pages:
            self._raise_if_cancelled(cancel_event)
            page_text = (page or {}).get("text", "")
            section_key = (page or {}).get("section_key", "document_overview")
            section_topic = (page or {}).get("section_topic", "Document Overview")
            if page_text and page_text.strip():
                section_text_by_key.setdefault(section_key, []).append(page_text)
            section_topic_by_key[section_key] = section_topic

        section_context_by_key = {
            key: "\n".join(chunks)[:8000]
            for key, chunks in section_text_by_key.items()
        }

        page_results = []
        page_summaries = []
        aggregate_verdicts = []
        for page in sectionized_pages:
            self._raise_if_cancelled(cancel_event)
            page_text = (page or {}).get("text", "")
            if not page_text or not page_text.strip():
                continue

            page_number = (page or {}).get("page_number")
            page_source = (page or {}).get("source")
            section_key = (page or {}).get("section_key", "document_overview")
            section_topic = (page or {}).get("section_topic", "Document Overview")
            summary_start = time.time()
            page_context_summary = await asyncio.to_thread(self._generate_context_summary, page_text, section_topic)
            print(f"PDF page {page_number} context summary:", round(time.time() - summary_start, 3), "sec")
            selection_start = time.time()
            self._emit_progress(
                progress_callback,
                stage="claim_selection",
                status="active",
                detail=f"Selecting claim from page {page_number}",
                substep=f"page_{page_number}",
                substatus="active",
            )
            await self._flush_progress()
            selection = await asyncio.to_thread(
                self._select_text_main_claim,
                page_text,
                self._should_use_pdf_fast_path(page),
            )
            print(f"PDF page {page_number} claim selection:", round(time.time() - selection_start, 3), "sec")
            self._emit_progress(
                progress_callback,
                stage="claim_selection",
                status="active",
                detail=f"Selected claim on page {page_number}",
                substep=f"page_{page_number}",
                substatus="done",
            )
            await self._flush_progress()
            selected_claim = selection.get("claim")

            for stage_id in ("structured_api", "web_search", "extraction", "relevance", "stance", "verdict"):
                self._emit_progress(
                    progress_callback,
                    stage=stage_id,
                    status="pending",
                    detail=f"Waiting for page {page_number}",
                )
            await self._flush_progress()

            page_pipeline_start = time.time()
            page_result = await self._process_text(
                page_text,
                ocr_details=None,
                selected_claim=selected_claim,
                source_text=section_context_by_key.get(section_key) or page_text,
                source_language=source_language,
                source_modality="pdf",
                allow_llm_verifier=True,
                cancel_event=cancel_event,
                progress_callback=progress_callback,
            )
            print(f"PDF page {page_number} claim pipeline:", round(time.time() - page_pipeline_start, 3), "sec")
            if isinstance(page_result, dict):
                page_rows = page_result.get("results") if isinstance(page_result.get("results"), list) else []
                page_claim_result = dict(page_rows[0]) if page_rows and isinstance(page_rows[0], dict) else dict(page_result)
                page_claim_result["page_number"] = page_number
                page_claim_result["page_source"] = page_source
                page_claim_result["section_topic"] = section_topic
                page_claim_result["page_analysis"] = page_result
                page_results.append(page_claim_result)

                evidence_rows = page_claim_result.get("evidence") if isinstance(page_claim_result.get("evidence"), list) else []
                strong_rows = [
                    row for row in evidence_rows
                    if str((row or {}).get("evidence_tier", "")).lower() == "strong"
                ]
                strongest_row = None
                if evidence_rows:
                    strongest_row = max(
                        evidence_rows,
                        key=lambda row: float((row or {}).get("combined_score", 0.0) or 0.0),
                    )

                page_summaries.append({
                    "page_number": page_number,
                    "page_source": page_source,
                    "section_topic": section_topic,
                    "page_context_summary": page_context_summary,
                    "text_preview": page_text[:240],
                    "selected_claim": selected_claim,
                    "selection_reason": selection.get("reason"),
                    "selected_claim_score": selection.get("score"),
                    "selected_claim_candidates": selection.get("candidates", [])[:3],
                    "final_verdict": page_claim_result.get("final_verdict"),
                    "confidence": page_claim_result.get("confidence"),
                })
                aggregate_verdicts.append({
                    "page_number": page_number,
                    "section_topic": section_topic,
                    "section_summary": self._build_section_summary(page_text, selected_claim),
                    "page_context_summary": page_context_summary,
                    "verdict": page_claim_result.get("final_verdict"),
                    "confidence": page_claim_result.get("confidence"),
                    "evidence_strength": "strong" if strong_rows else ("soft" if evidence_rows else "none"),
                    "evidence_count": len(evidence_rows),
                    "conflict_analysis": page_claim_result.get("conflict_analysis"),
                    "strongest_evidence": {
                        "stance": (strongest_row or {}).get("stance"),
                        "source": (strongest_row or {}).get("source"),
                        "url": (strongest_row or {}).get("url"),
                        "text_preview": ((strongest_row or {}).get("text") or "")[:220],
                    } if strongest_row else None,
                })

        document_score = score_document(page_results)

        section_overview_map = {}
        for row in page_results:
            section_topic = row.get("section_topic") or "Document Overview"
            section_key = self._normalize_section_key(section_topic)
            bucket = section_overview_map.setdefault(section_key, {
                "section_topic": section_topic,
                "pages": [],
                "true_claims": 0,
                "false_claims": 0,
                "neutral_claims": 0,
            })
            page_number = row.get("page_number")
            if page_number is not None:
                bucket["pages"].append(page_number)

            verdict = str(row.get("final_verdict") or "").upper()
            if verdict == "TRUE":
                bucket["true_claims"] += 1
            elif verdict == "FALSE":
                bucket["false_claims"] += 1
            else:
                bucket["neutral_claims"] += 1

        section_overview = []
        for section_key, bucket in section_overview_map.items():
            if bucket["false_claims"] > 0 and bucket["false_claims"] >= bucket["true_claims"]:
                section_verdict = "Likely Unreliable"
            elif bucket["true_claims"] > 0 and bucket["false_claims"] == 0:
                section_verdict = "Likely Reliable"
            else:
                section_verdict = "Mixed / Needs Review"

                section_overview.append({
                "section_topic": bucket["section_topic"],
                "pages": sorted(bucket["pages"]),
                "claims_analyzed": len(bucket["pages"]),
                "true_claims": bucket["true_claims"],
                "false_claims": bucket["false_claims"],
                "neutral_claims": bucket["neutral_claims"],
                "section_verdict": section_verdict,
                "section_context_summary": await asyncio.to_thread(
                    self._generate_context_summary,
                    section_context_by_key.get(section_key, ""),
                    bucket["section_topic"],
                ),
            })

        self._emit_progress(
            progress_callback,
            stage="verdict",
            status="active",
            detail=f"Aggregating document verdict across {len(page_results)} page(s)",
        )
        await self._flush_progress()
        total_elapsed = round(time.time() - total_start, 3)
        print("TOTAL PDF DOCUMENT PIPELINE TIME:", total_elapsed, "sec")
        self._emit_progress(
            progress_callback,
            stage="verdict",
            status="done",
            detail=f"{document_score['verdict']} across {len(page_results)} page(s)",
        )
        await self._flush_progress()
        return {
            "source_url": None,
            "ocr_details": ocr_details,
            "total_pages_detected": total_pages_detected,
            "claims_analyzed": len(page_results),
            "pages_analyzed": len(page_results),
            "analysis_warning": analysis_warning,
            "pdf_analysis_max_pages": self.pdf_analysis_max_pages,
            "true_claims": document_score["true"],
            "false_claims": document_score["false"],
            "neutral_claims": document_score["neutral"],
            "document_credibility_score": document_score["score"],
            "document_verdict": document_score["verdict"],
            "context_summarizer_mode": self._resolved_summary_mode(),
            "pipeline_timing_seconds": {
                "total": total_elapsed,
            },
            "page_results": page_summaries,
            "aggregate_verdicts": aggregate_verdicts,
            "section_overview": section_overview,
            "results": page_results,
        }

    async def process_image(self, file_path, cancel_event=None, progress_callback=None):
        total_start = time.time()
        self._emit_progress(progress_callback, stage="ocr", status="active", detail="Running OCR on uploaded image")
        await self._flush_progress()
        self._raise_if_cancelled(cancel_event)
        ocr_start = time.time()
        ocr_result = await asyncio.to_thread(extract_image_text, file_path)
        ocr_elapsed = round(time.time() - ocr_start, 3)
        print("Image OCR:", ocr_elapsed, "sec")
        self._emit_progress(progress_callback, stage="ocr", status="done", detail=f"OCR complete in {ocr_elapsed} sec")
        await self._flush_progress()
        self._raise_if_cancelled(cancel_event)
        text = (ocr_result or {}).get("text", "")
        source_language = self._infer_source_language(text, ocr_result)
        if not text:
            return {"error": "Could not extract text"}
        if not (ocr_result or {}).get("usable", False):
            return {
                "error": "Could not reliably extract text from image",
                "ocr_details": {
                    "reason": ocr_result.get("reason"),
                    "avg_confidence": ocr_result.get("avg_confidence"),
                    "word_count": ocr_result.get("word_count"),
                    "script_ratio": ocr_result.get("script_ratio"),
                    "ocr_langs": ocr_result.get("ocr_langs"),
                    "text_preview": text[:240],
                },
            }

        selection_start = time.time()
        self._emit_progress(progress_callback, stage="claim_selection", status="active", detail="Selecting central claim from OCR text")
        await self._flush_progress()
        selection = await asyncio.to_thread(self._select_image_main_claim, text)
        selection_elapsed = round(time.time() - selection_start, 3)
        print("Image claim selection:", selection_elapsed, "sec")
        self._emit_progress(progress_callback, stage="claim_selection", status="done", detail=f"Claim selected in {selection_elapsed} sec")
        await self._flush_progress()
        candidate_claims = []
        seen_candidates = set()
        for candidate in (selection.get("top_claims") or []):
            cleaned = self._clean_image_candidate(candidate)
            if not cleaned:
                continue
            key = re.sub(r"\W+", " ", cleaned.lower(), flags=re.UNICODE).strip()
            if not key or key in seen_candidates:
                continue
            seen_candidates.add(key)
            candidate_claims.append(cleaned)
        main_claim = selection.get("claim")
        if main_claim:
            cleaned_main = self._clean_image_candidate(main_claim)
            if cleaned_main:
                key = re.sub(r"\W+", " ", cleaned_main.lower(), flags=re.UNICODE).strip()
                if key not in seen_candidates:
                    candidate_claims.insert(0, cleaned_main)
                    seen_candidates.add(key)
        if not candidate_claims and main_claim:
            candidate_claims = [main_claim]
        if not candidate_claims:
            return {
                "error": "Could not isolate a central factual claim from image text",
                "ocr_details": {
                    "reason": "claim_selection_failed",
                    "text_preview": text[:240],
                    "selected_claim_candidates": selection.get("candidates", [])[:3],
                },
            }

        source_language = detect_language(candidate_claims[0] or text)

        enriched_ocr = dict(ocr_result)
        enriched_ocr["selected_claim"] = candidate_claims[0]
        enriched_ocr["selection_reason"] = selection.get("reason")
        enriched_ocr["selected_claim_score"] = selection.get("score")
        enriched_ocr["selected_claim_candidates"] = selection.get("candidates", [])[:3]
        enriched_ocr["selected_claims"] = candidate_claims[:3]

        claim_pipeline_start = time.time()
        candidate_results = []
        for candidate_claim in candidate_claims[:3]:
            self._raise_if_cancelled(cancel_event)
            candidate_result = await self._process_text(
                text,
                ocr_details=enriched_ocr,
                selected_claim=candidate_claim,
                source_text=text,
                source_language=source_language,
                source_modality="image",
                allow_llm_verifier=True,
                cancel_event=cancel_event,
                progress_callback=progress_callback,
            )
            if isinstance(candidate_result, dict):
                normalized_candidate = dict(candidate_result)
                nested_rows = normalized_candidate.get("results")
                if isinstance(nested_rows, list) and nested_rows and isinstance(nested_rows[0], dict):
                    # Flatten the top claim result so scoring reads real verdict/confidence values.
                    normalized_candidate.update(dict(nested_rows[0]))
                normalized_candidate["selected_claim"] = candidate_claim
                candidate_result = normalized_candidate
            candidate_results.append(candidate_result)

        def image_result_score(item):
            if not isinstance(item, dict):
                return (-1.0, -1.0, -1.0)
            verdict = str(item.get("final_verdict") or "NEUTRAL").upper()
            confidence = float(item.get("confidence", 0.0) or 0.0)
            verdict_bonus = 1.0 if verdict in {"TRUE", "FALSE"} else 0.4
            support_count = len([ev for ev in item.get("evidence", []) if str((ev or {}).get("stance", "")).upper() in {"SUPPORT", "REFUTE"}])
            return (verdict_bonus, confidence, float(support_count))

        if candidate_results:
            best_index = max(range(len(candidate_results)), key=lambda idx: image_result_score(candidate_results[idx]))
            result = candidate_results[best_index]
        else:
            best_index = None
            result = {"error": "Could not analyze image claim candidates"}

        if isinstance(result, dict):
            winning_claim = None
            if best_index is not None and 0 <= best_index < len(candidate_claims):
                winning_claim = result.get("selected_claim") or candidate_claims[best_index]
                result["claim"] = winning_claim
                result["selected_claim"] = winning_claim
            candidate_summaries = []
            for idx, item in enumerate(candidate_results):
                if not isinstance(item, dict):
                    continue
                candidate_summaries.append({
                    "candidate_index": idx,
                    "selected_claim": item.get("selected_claim"),
                    "final_verdict": item.get("final_verdict"),
                    "confidence": item.get("confidence"),
                    "conflict_analysis": item.get("conflict_analysis"),
                    "evidence_count": len(item.get("evidence", []) or []),
                })

            result["image_candidate_results"] = candidate_summaries
            result["image_selected_candidate_index"] = best_index
            result["image_selected_candidates"] = candidate_claims[:3]
            ocr_details_result = result.get("ocr_details")
            if isinstance(ocr_details_result, dict):
                if winning_claim:
                    ocr_details_result["selected_claim"] = winning_claim
                ocr_details_result["selected_claim_preanalysis"] = candidate_claims[0] if candidate_claims else None
                ocr_details_result["selected_claims"] = candidate_claims[:3]
        claim_pipeline_elapsed = round(time.time() - claim_pipeline_start, 3)
        total_elapsed = round(time.time() - total_start, 3)
        print("Image document->claim pipeline:", claim_pipeline_elapsed, "sec")
        print("TOTAL IMAGE DOCUMENT PIPELINE TIME:", total_elapsed, "sec")
        if isinstance(result, dict):
            result["pipeline_timing_seconds"] = {
                "ocr": ocr_elapsed,
                "claim_selection": selection_elapsed,
                "claim_pipeline": claim_pipeline_elapsed,
                "total": total_elapsed,
            }
        return result

    def _clean_image_candidate(self, text):
        cleaned = re.sub(r"\s+", " ", (text or "")).strip(" -\t\r\n|:;,.")
        cleaned = re.sub(r"^[\u2022\u2023\u25E6\u2043\-\*\#]+\s*", "", cleaned)
        return cleaned.strip()

    def _extract_page_heading(self, page_text):
        heading_keywords = {
            "introduction", "overview", "background", "impact", "assessment",
            "components", "environment", "management", "plan", "sources",
            "conclusion", "framework", "summary", "findings"
        }
        bad_phrase_pattern = re.compile(
            r"\b(for example|in particular|for instance|would have|could|should|were|was|are|is)\b",
            flags=re.IGNORECASE,
        )

        for raw_line in re.split(r"[\r\n]+", page_text or ""):
            line = self._clean_image_candidate(raw_line)
            if not line:
                continue

            words = line.split()
            if len(words) < 2 or len(words) > 8:
                continue
            if re.search(r"[.!?,;()]", line):
                continue
            if bad_phrase_pattern.search(line):
                continue
            if not (re.search(r"[A-Za-z]", line) or re.search(r"[\u0900-\u0D7F]", line)):
                continue

            lower_words = [re.sub(r"[^a-z]", "", w.lower()) for w in words]
            lower_words = [w for w in lower_words if w]
            if not lower_words:
                continue

            has_keyword = any(w in heading_keywords for w in lower_words)
            title_case_ratio = sum(1 for w in words if w[:1].isupper()) / max(len(words), 1)

            # Skip likely author-name lines such as "John Doe".
            is_name_like = (
                2 <= len(words) <= 3
                and all(re.match(r"^[A-Z][a-z]+$", w) for w in words)
                and not has_keyword
            )
            if is_name_like:
                continue

            if has_keyword or title_case_ratio >= 0.55:
                return line
        return None

    def _build_section_summary(self, page_text, selected_claim):
        heading = self._extract_page_heading(page_text)
        claim = self._clean_image_candidate(selected_claim or "")
        if claim:
            claim = re.sub(r"[\u2022\u2023\u25E6\u2043]+", " ", claim)
            claim = re.sub(r"\s+", " ", claim).strip()
            claim = claim[:220].rstrip(" ,;:-")

        if heading and claim:
            heading_norm = re.sub(r"\W+", " ", heading.lower()).strip()
            claim_norm = re.sub(r"\W+", " ", claim.lower()).strip()
            if heading_norm and claim_norm.startswith(heading_norm):
                return claim
            return f"{heading}: {claim}"
        if claim:
            return claim

        return self._clean_image_candidate((page_text or "")[:220])

    def _normalize_section_key(self, topic):
        cleaned = re.sub(r"\W+", " ", (topic or "").lower()).strip()
        return cleaned.replace(" ", "_") or "document_overview"

    def _assign_sections_to_pages(self, pages):
        assigned = []
        current_topic = "Document Overview"

        for page in pages:
            page_text = (page or {}).get("text", "")
            detected = self._extract_page_heading(page_text)
            if detected:
                current_topic = detected

            row = dict(page or {})
            row["section_topic"] = current_topic
            row["section_key"] = self._normalize_section_key(current_topic)
            assigned.append(row)

        return assigned

    def _heading_alignment_bonus(self, heading, candidate_text):
        heading_norm = re.sub(r"\s+", " ", (heading or "")).strip().lower()
        candidate_norm = re.sub(r"\s+", " ", (candidate_text or "")).strip().lower()
        if not heading_norm or not candidate_norm:
            return 0.0

        heading_tokens = set(re.findall(r"[a-z0-9]{3,}", heading_norm))
        candidate_tokens = set(re.findall(r"[a-z0-9]{3,}", candidate_norm))
        if not heading_tokens or not candidate_tokens:
            return 0.0

        overlap = len(heading_tokens & candidate_tokens)
        if overlap <= 0:
            return 0.0

        return min(0.18, overlap * 0.06)

    def _resolved_summary_mode(self):
        mode = (getattr(self, "context_summary_mode", "extractive") or "extractive").lower().strip()
        if mode == "off":
            return "off"
        if mode == "llm" and getattr(self, "context_llm_enabled", False) and bool(getattr(self, "context_llm_api_key", None)):
            return "llm"
        return "extractive"

    def _generate_context_summary(self, text, topic=None):
        mode = self._resolved_summary_mode()
        if mode == "off":
            return ""
        if mode == "llm":
            llm_summary = self._summarize_with_llm(text, topic=topic)
            if llm_summary:
                return llm_summary
        return self._summarize_extractive(text, topic=topic)

    def _summarize_extractive(self, text, topic=None):
        max_chars = max(120, int(getattr(self, "context_summary_max_chars", 280) or 280))
        max_sentences = max(1, int(getattr(self, "context_summary_max_sentences", 2) or 2))
        normalized = re.sub(r"\s+", " ", (text or "")).strip()
        if not normalized:
            return ""

        sentences = [
            s.strip() for s in re.split(r"(?<=[.!?\u0964])\s+", normalized)
            if s and s.strip()
        ]
        if not sentences:
            return normalized[:max_chars].rstrip(" ,;:-")

        topic_tokens = set(re.findall(r"[a-z0-9]{3,}", (topic or "").lower()))
        scored = []
        for idx, sentence in enumerate(sentences[:12]):
            lowered = sentence.lower()
            sent_tokens = set(re.findall(r"[a-z0-9]{3,}", lowered))
            overlap = len(sent_tokens & topic_tokens)
            factual_bonus = 1.0 if (re.search(r"\d", sentence) or re.search(r"\b(is|are|was|were|has|have|had)\b", lowered)) else 0.0
            lead_bonus = max(0.0, 1.0 - (idx * 0.08))
            length_penalty = 0.0 if 8 <= len(sentence.split()) <= 42 else 0.25
            score = (overlap * 1.6) + factual_bonus + lead_bonus - length_penalty
            scored.append((score, idx, sentence))

        scored.sort(key=lambda item: item[0], reverse=True)
        selected = sorted(scored[:max_sentences], key=lambda item: item[1])
        summary = " ".join(item[2] for item in selected).strip()
        if len(summary) > max_chars:
            summary = summary[:max_chars].rsplit(" ", 1)[0]
        return summary.rstrip(" ,;:-")

    def _summarize_with_llm(self, text, topic=None):
        if not text or not text.strip():
            return ""
        if not (getattr(self, "context_llm_enabled", False) and bool(getattr(self, "context_llm_api_key", None))):
            return ""

        snippet = re.sub(r"\s+", " ", text).strip()[:3000]
        topic_text = (topic or "Document section").strip()
        prompt = (
            "Write a concise factual context summary for fact-checking. "
            "Keep it to 1-2 sentences and focus on verifiable statements only. "
            f"Topic: {topic_text}\n"
            f"Text: {snippet}"
        )

        payload = {
            "model": getattr(self, "context_llm_model", "gpt-4o-mini"),
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": "You summarize documents for factual verification pipelines."},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {getattr(self, 'context_llm_api_key', '')}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                f"{getattr(self, 'context_llm_api_base', 'https://api.openai.com/v1')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=float(getattr(self, "context_llm_timeout", 30)),
            )
            response.raise_for_status()
            data = response.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            summary = re.sub(r"\s+", " ", (content or "")).strip()
            max_chars = max(120, int(getattr(self, "context_summary_max_chars", 280) or 280))
            if len(summary) > max_chars:
                summary = summary[:max_chars].rsplit(" ", 1)[0]
            return summary.rstrip(" ,;:-")
        except Exception:
            return ""

    def _image_sentence_candidates(self, text):
        if not text:
            return []

        line_parts = []
        for raw_line in re.split(r"[\r\n]+", text):
            cleaned = self._clean_image_candidate(raw_line)
            if cleaned:
                line_parts.append(cleaned)

        candidate_parts = list(line_parts)
        for idx in range(len(line_parts) - 1):
            merged = self._clean_image_candidate(f"{line_parts[idx]} {line_parts[idx + 1]}")
            if merged:
                candidate_parts.append(merged)

        normalized = re.sub(r"\s+", " ", (text or "")).strip()
        candidate_parts.extend(re.split(r"(?<=[.!?\u0964])\s+|\s{2,}", normalized))

        candidates = []
        seen = set()
        for idx, part in enumerate(candidate_parts):
            sentence = self._clean_image_candidate(part)
            if not sentence:
                continue
            words = sentence.split()
            if len(words) < 5 or len(words) > 32:
                continue
            key = re.sub(r"\W+", " ", sentence.lower(), flags=re.UNICODE).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            candidates.append((idx, sentence))
        return candidates

    def _image_block_candidates(self, text):
        sentence_candidates = self._image_sentence_candidates(text)
        if not sentence_candidates:
            return []

        blocks = []
        seen = set()
        max_sentence_window = min(3, len(sentence_candidates))

        for idx, (_, sentence) in enumerate(sentence_candidates):
            cleaned = self._clean_image_candidate(sentence)
            if cleaned:
                key = re.sub(r"\W+", " ", cleaned.lower(), flags=re.UNICODE).strip()
                if key and key not in seen:
                    seen.add(key)
                    blocks.append((idx, cleaned))

            for window in range(2, max_sentence_window + 1):
                if idx + window > len(sentence_candidates):
                    break
                merged = self._clean_image_candidate(
                    " ".join(sentence_candidates[idx + offset][1] for offset in range(window))
                )
                words = merged.split()
                if len(words) < 8 or len(words) > 55:
                    continue
                key = re.sub(r"\W+", " ", merged.lower(), flags=re.UNICODE).strip()
                if key and key not in seen:
                    seen.add(key)
                    blocks.append((idx, merged))

        return blocks

    @staticmethod
    def _image_candidate_key(text):
        normalized = re.sub(r"\s+", " ", (text or "")).strip().lower()
        normalized = re.sub(r"[^\w\u0900-\u0D7F]+", " ", normalized, flags=re.UNICODE)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _distinct_top_image_candidates(self, scored_candidates, limit=3):
        selected = []
        seen = []
        for item in scored_candidates:
            text = self._clean_image_candidate(item.get("text"))
            if not text:
                continue
            key = self._image_candidate_key(text)
            if not key:
                continue

            tokens = set(re.findall(r"[\w\u0900-\u0D7F]{3,}", key, flags=re.UNICODE))
            duplicate = False
            for existing_key, existing_tokens in seen:
                if key == existing_key:
                    duplicate = True
                    break
                if tokens and existing_tokens and len(tokens & existing_tokens) / max(len(tokens | existing_tokens), 1) >= 0.72:
                    duplicate = True
                    break
                if key in existing_key or existing_key in key:
                    duplicate = True
                    break
            if duplicate:
                continue

            selected.append(item)
            seen.append((key, tokens))
            if len(selected) >= limit:
                break
        return selected

    def _model_score_image_candidate(self, document_text, candidate_text):
        cleaned = self._clean_image_candidate(candidate_text)
        if not cleaned:
            return {
                "text": "",
                "score": -1.0,
                "semantic_score": 0.0,
                "claim_type": "unknown",
                "checkable": False,
                "checkability_code": "empty_claim",
            }

        claim_type = self.claim_pipeline.claim_type_classifier.classify(cleaned)
        logical = self.claim_pipeline.logical_analyzer.analyze(cleaned)
        checkability = self.claim_pipeline.claim_checkability.classify(
            cleaned,
            claim_type_result=claim_type,
            logical_metadata=logical,
        )
        semantic_score = float(self.claim_pipeline.relevance_scorer.semantic_score(document_text, cleaned))
        claim_type_value = str(getattr(claim_type.get("type"), "value", claim_type.get("type", ""))).lower()
        claim_type_conf = float(
            claim_type.get("model_confidence", claim_type.get("confidence", 0.0)) or 0.0
        )
        checkability_conf = float(checkability.get("confidence", 0.0) or 0.0)

        if claim_type_value in {"factual", "numerical"}:
            type_score = claim_type_conf
        elif claim_type_value == "mixed":
            type_score = claim_type_conf * 0.5
        else:
            type_score = -claim_type_conf

        checkability_score = checkability_conf if checkability.get("allowed") else -checkability_conf
        final_score = (
            (semantic_score * 0.55)
            + (checkability_score * 0.3)
            + (type_score * 0.15)
        )
        return {
            "text": cleaned,
            "score": round(final_score, 4),
            "semantic_score": round(semantic_score, 4),
            "claim_type": claim_type_value,
            "claim_type_confidence": round(claim_type_conf, 4),
            "checkable": bool(checkability.get("allowed")),
            "checkability_confidence": round(checkability_conf, 4),
            "checkability_code": checkability.get("code"),
        }

    def _is_clean_paragraph_ocr_text(self, text):
        normalized = re.sub(r"\s+", " ", (text or "")).strip()
        if not normalized:
            return False

        words = normalized.split()
        if len(words) < 14 or len(words) > 400:
            return False

        raw_lines = [line.strip() for line in re.split(r"[\r\n]+", text or "") if line and line.strip()]
        if len(raw_lines) > 2:
            return False
        if len(raw_lines) == 2 and min(len(raw_lines[0].split()), len(raw_lines[1].split())) < 8:
            return False

        bullet_like_lines = sum(
            1
            for line in raw_lines
            if re.match(r"^(?:[\u2022\u2023\u25E6\u2043\-*#]|\d+[.)])\s+", line)
        )
        if bullet_like_lines > 0:
            return False

        punctuation_count = len(re.findall(r"[.!?\u0964]", normalized))
        has_sentence_signal = punctuation_count >= 1 or len(words) >= 24
        return has_sentence_signal

    def _is_pdf_text_fast_path_candidate(self, text, max_words=70, max_chars=520, max_lines=6):
        normalized = re.sub(r"\s+", " ", (text or "")).strip()
        if not normalized:
            return False

        words = normalized.split()
        if len(words) < 14 or len(words) > int(max_words):
            return False

        text_chars = len(normalized)
        if text_chars > int(max_chars):
            return False

        raw_lines = [line.strip() for line in re.split(r"[\r\n]+", text or "") if line and line.strip()]
        if len(raw_lines) > int(max_lines):
            return False

        punctuation_count = len(re.findall(r"[.!?\u0964]", normalized))
        has_sentence_signal = punctuation_count >= 1 or len(words) >= 24
        return has_sentence_signal

    def _pdf_section_gate_modifier(self, page):
        topic = str((page or {}).get("section_topic", "") or "").lower().strip()
        if not topic:
            return "neutral"

        block_keywords = {
            "reference", "references", "appendix", "annex", "bibliography",
            "methodology", "methods", "table of contents", "index", "glossary",
            "acknowledgement", "acknowledgment",
        }
        prefer_keywords = {
            "summary", "overview", "highlights", "key findings", "key points",
            "alert", "bulletin", "update", "breaking",
        }

        if any(keyword in topic for keyword in block_keywords):
            return "block"
        if any(keyword in topic for keyword in prefer_keywords):
            return "prefer"
        return "neutral"

    def _should_use_pdf_fast_path(self, page):
        page_text = (page or {}).get("text", "")
        source = str((page or {}).get("source", "")).lower().strip()
        section_modifier = self._pdf_section_gate_modifier(page)

        if section_modifier == "block":
            return False

        if source == "ocr":
            return self._is_clean_paragraph_ocr_text(page_text)

        # Primary short-style gate for text-layer PDF pages.
        if self._is_pdf_text_fast_path_candidate(page_text):
            return True

        # Secondary heading-aware relaxation for summary/alert-like sections only.
        if section_modifier == "prefer":
            return self._is_pdf_text_fast_path_candidate(
                page_text,
                max_words=90,
                max_chars=700,
                max_lines=8,
            )

        return False

    def _extract_main_claim_lightweight(self, text):
        claim = self._clean_image_candidate(self.extractor.extract_main_claim(text))
        if claim:
            return claim

        normalized = re.sub(r"\s+", " ", (text or "")).strip()
        for sentence in re.split(r"(?<=[.!?\u0964])\s+", normalized):
            cleaned = self._clean_image_candidate(sentence)
            if not cleaned:
                continue
            words = cleaned.split()
            if len(words) < 6:
                continue
            if re.search(r"\d", cleaned) or re.search(r"\b(is|are|was|were|has|have|had)\b", cleaned, flags=re.IGNORECASE):
                return cleaned

        return self._clean_image_candidate(normalized[:260])

    def _synthesize_claim_from_block(self, text, full_text=None):
        cleaned = self._clean_image_candidate(text)
        if not cleaned:
            return ""

        source_text = full_text if full_text is not None else cleaned
        all_sentences = [
            candidate_text
            for _, candidate_text in self._image_sentence_candidates(source_text)
        ]
        sentences = [sentence for sentence in all_sentences if sentence and sentence in cleaned]
        if not sentences:
            sentences = [
                self._clean_image_candidate(part)
                for part in re.split(r"(?<=[.!?\u0964])\s+", cleaned)
                if self._clean_image_candidate(part)
            ]
        if not sentences:
            return cleaned

        ranked = [
            self._model_score_image_candidate(cleaned, sentence)
            for sentence in sentences
        ]
        ranked.sort(key=lambda item: item["score"], reverse=True)
        if not ranked:
            return cleaned

        best = ranked[0] or {}
        best_text = self._clean_image_candidate(best.get("text", cleaned))
        best_word_count = len(best_text.split()) if best_text else 0

        if best_word_count > 24:
            compact_candidates = [
                item for item in ranked
                if 6 <= len((item.get("text") or "").split()) <= 24
            ]
            if compact_candidates:
                compact_candidates.sort(key=lambda item: item["score"], reverse=True)
                compact_text = self._clean_image_candidate((compact_candidates[0] or {}).get("text", ""))
                if compact_text:
                    return compact_text

        return best_text or cleaned

    def _select_text_main_claim(self, text, prefer_fast_path=False):
        if prefer_fast_path and (
            self._is_clean_paragraph_ocr_text(text)
            or self._is_pdf_text_fast_path_candidate(text)
        ):
            claim = self._extract_main_claim_lightweight(text)
            return {
                "claim": claim,
                "reason": "ocr_clean_text_fast_path",
                "score": None,
                "candidates": [],
            }

        claim_candidates = []
        seen = set()

        for candidate in self.extractor.extract_claims(text):
            cleaned = self._clean_image_candidate(candidate)
            if not cleaned:
                continue
            key = re.sub(r"\W+", " ", cleaned.lower(), flags=re.UNICODE).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            claim_candidates.append(cleaned)

        if not claim_candidates:
            return {
                "claim": self.extractor.extract_main_claim(text),
                "reason": "extractor_fallback",
                "score": None,
                "candidates": [],
            }

        scored = [
            self._model_score_image_candidate(text, candidate_text)
            for candidate_text in claim_candidates
        ]
        heading = self._extract_page_heading(text)
        if heading:
            for item in scored:
                base_score = float(item.get("score", 0.0) or 0.0)
                bonus = self._heading_alignment_bonus(heading, item.get("text", ""))
                if bonus <= 0.0:
                    continue
                item["base_score"] = round(base_score, 4)
                item["heading_bonus"] = round(bonus, 4)
                item["score"] = round(base_score + bonus, 4)

        scored.sort(key=lambda item: item["score"], reverse=True)
        best = scored[0] if scored else None
        if not best:
            return {
                "claim": self.extractor.extract_main_claim(text),
                "reason": "extractor_fallback_after_no_score",
                "score": None,
                "candidates": [],
            }

        if not best.get("checkable") and best.get("score", -1.0) < 0.35:
            return {
                "claim": self.extractor.extract_main_claim(text),
                "reason": "extractor_fallback_after_low_score",
                "score": best.get("score"),
                "candidates": scored,
            }

        def selection_rank(item):
            candidate_text = self._clean_image_candidate(item.get("text", ""))
            word_count = len(candidate_text.split()) if candidate_text else 0
            base_score = float(item.get("score", -1.0) or -1.0)
            punctuation_count = candidate_text.count(",") + candidate_text.count(";") + candidate_text.count(":")
            lead_context_penalty = 0.0
            if word_count > 0 and word_count < 6:
                lead_context_penalty = 0.08

            length_bonus = 0.0
            if 8 <= word_count <= 24:
                length_bonus = 0.08
            elif 25 <= word_count <= 34:
                length_bonus = 0.03
            elif word_count > 40:
                length_bonus = -0.06
            elif word_count > 28:
                length_bonus = -0.03

            punctuation_penalty = min(0.10, punctuation_count * 0.02)
            return base_score + length_bonus - punctuation_penalty - lead_context_penalty

        ranked_selection = sorted(scored, key=selection_rank, reverse=True)
        selected_best = ranked_selection[0] if ranked_selection else best
        selected_text = self._clean_image_candidate((selected_best or {}).get("text", ""))

        return {
            "claim": selected_text or best["text"],
            "reason": "page_context_selector",
            "score": (selected_best or best).get("score"),
            "candidates": ranked_selection,
        }

    def _select_image_main_claim(self, text):
        candidates = self._image_block_candidates(text)
        if not candidates:
            return {
                "claim": self.extractor.extract_main_claim(text),
                "reason": "extractor_fallback",
                "score": None,
                "candidates": [],
            }

        scored = [
            self._model_score_image_candidate(text, candidate_text)
            for _, candidate_text in candidates
        ]
        scored.sort(key=lambda item: item["score"], reverse=True)
        scored = self._distinct_top_image_candidates(scored, limit=3)
        best = scored[0] if scored else None
        if not best:
            return {
                "claim": None,
                "reason": "no_candidates",
                "score": None,
                "candidates": [],
            }

        if not best.get("checkable") and best.get("score", -1.0) < 0.35:
            return {
                "claim": self.extractor.extract_main_claim(text),
                "reason": "extractor_fallback_after_low_score",
                "score": best.get("score"),
                "candidates": scored,
            }

        synthesized_claim = self._synthesize_claim_from_block(best["text"], full_text=text)
        ranked_candidates = sorted(scored, key=lambda item: item["score"], reverse=True)
        concise_top_claims = []
        seen_claims = set()
        seen_tokens = []
        for item in ranked_candidates[:5]:
            raw_block = item.get("text", "")
            concise = self._synthesize_claim_from_block(raw_block, full_text=text)
            concise = self._clean_image_candidate(concise)[:260]
            key = self._image_candidate_key(concise)
            if not concise or not key or key in seen_claims:
                continue

            tokens = set(re.findall(r"[\w\u0900-\u0D7F]{3,}", key, flags=re.UNICODE))
            if tokens and any(
                prev_tokens and len(tokens & prev_tokens) / max(len(tokens | prev_tokens), 1) >= 0.70
                for prev_tokens in seen_tokens
            ):
                continue

            seen_claims.add(key)
            seen_tokens.append(tokens)
            concise_top_claims.append(concise)
            if len(concise_top_claims) >= 3:
                break

        # Backfill with high-scoring raw blocks when synthesized claims collapse into a single variant.
        if len(concise_top_claims) < 3:
            for item in ranked_candidates[:10]:
                raw_candidate = self._clean_image_candidate(item.get("text", ""))[:260]
                key = self._image_candidate_key(raw_candidate)
                if not raw_candidate or not key or key in seen_claims:
                    continue

                raw_tokens = set(re.findall(r"[\w\u0900-\u0D7F]{3,}", key, flags=re.UNICODE))
                if raw_tokens and any(
                    prev_tokens and len(raw_tokens & prev_tokens) / max(len(raw_tokens | prev_tokens), 1) >= 0.90
                    for prev_tokens in seen_tokens
                ):
                    continue

                seen_claims.add(key)
                seen_tokens.append(raw_tokens)
                concise_top_claims.append(raw_candidate)
                if len(concise_top_claims) >= 3:
                    break

        if not concise_top_claims and best.get("text"):
            fallback_claim = self._clean_image_candidate(best.get("text"))[:260]
            if fallback_claim:
                concise_top_claims = [fallback_claim]

        selected_claim = concise_top_claims[0] if concise_top_claims else (synthesized_claim or best["text"])

        return {
            "claim": selected_claim,
            "reason": "existing_model_selector",
            "score": best["score"],
            "candidates": ranked_candidates,
            "source_block": best["text"],
            "top_claims": concise_top_claims,
        }

    async def _process_text(self, text, source_url=None, ocr_details=None, selected_claim=None, source_text=None, source_language=None, source_modality="text", allow_llm_verifier=True, cancel_event=None, progress_callback=None):
        self._raise_if_cancelled(cancel_event)

        if not text:
            return {"error": "Could not extract text"}

        words = (text or "").strip().split()
        if selected_claim is not None:
            main_claim = selected_claim
        elif ocr_details is not None:
            main_claim = self._select_image_main_claim(text).get("claim")
        elif source_url is None and 3 <= len(words) <= 20:
            main_claim = (text or "").strip()
        else:
            main_claim = self.extractor.extract_main_claim(text)
        if not main_claim:
            return {
                "error": (
                    "Text was extracted but no valid claims were detected. "
                    "Try a cleaner article PDF/URL or provide direct claim text."
                )
            }

        results = []
        claim_result = await self.claim_pipeline.run(
            main_claim,
            source_url=source_url,
            source_text=source_text,
            source_language=source_language,
            source_modality=source_modality,
            allow_llm_verifier=allow_llm_verifier,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
        )
        results.append(claim_result)

        document_score = score_document(results)

        return {
            "source_url": source_url,
            "ocr_details": ocr_details,
            "claims_analyzed": len(results),
            "true_claims": document_score["true"],
            "false_claims": document_score["false"],
            "neutral_claims": document_score["neutral"],
            "document_credibility_score": document_score["score"],
            "document_verdict": document_score["verdict"],
            "results": results
        }
