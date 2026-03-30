from pipeline.claim_pipeline import extract_best_sentences, _should_skip_claim_reporting_sentence


class RetrievalPipelineV2:
    def __init__(self, relevance_scorer, quality_scorer, strong_relevance_threshold=0.42, soft_relevance_threshold=0.28):
        self.relevance_scorer = relevance_scorer
        self.quality_scorer = quality_scorer
        self.strong_relevance_threshold = strong_relevance_threshold
        self.soft_relevance_threshold = soft_relevance_threshold

    def select_evidence(self, claim, evidence_raw, sentence_cache, context_result=None, trace=None):
        documents = []
        for ev in evidence_raw:
            text = ev.get("text") or ""
            if not text or len(text.split()) < 20:
                continue

            cache_key = (
                " ".join((claim or "").strip().lower().split()),
                ev.get("url", ""),
                hash(text),
                "v2",
            )
            candidates = sentence_cache.get(cache_key)
            if candidates is None:
                candidates = extract_best_sentences(
                    claim,
                    text,
                    self.relevance_scorer,
                    max_sentences=4,
                    source_name=ev.get("source"),
                    context_result=context_result,
                )
                sentence_cache[cache_key] = candidates
            if not candidates:
                continue

            passage_rows = []
            for candidate in candidates:
                sentence = candidate["text"]
                if _should_skip_claim_reporting_sentence(
                    claim,
                    sentence,
                    source_name=ev.get("source"),
                    context_result=context_result,
                ):
                    if trace is not None:
                        trace["evidence_selected"].append({
                            "url": ev.get("url"),
                            "sentence": sentence,
                            "skipped": "claim_reporting_sentence_v2",
                        })
                    continue
                relevance_score = self.relevance_scorer.score(claim, sentence)
                quality_score = self.quality_scorer.score(sentence)
                selector_score = float(candidate.get("selector_score", 0.0))
                final_score = round(min(1.0, (relevance_score * 0.75) + (selector_score * 0.25)), 3)
                evidence_tier = None
                if final_score >= self.strong_relevance_threshold and quality_score >= 0.35:
                    evidence_tier = "strong"
                elif final_score >= self.soft_relevance_threshold and quality_score >= 0.22:
                    evidence_tier = "soft"
                if evidence_tier is None:
                    continue
                passage_rows.append({
                    "source": ev["source"],
                    "url": ev["url"],
                    "text": sentence,
                    "context_text": candidate.get("context_text", sentence),
                    "weight": ev["weight"],
                    "raw_weight": ev["weight"],
                    "relevance_score": final_score,
                    "base_relevance_score": relevance_score,
                    "selector_score": selector_score,
                    "reporting_penalty": float(candidate.get("reporting_penalty", 0.0)),
                    "lead_bonus": float(candidate.get("lead_bonus", 0.0)),
                    "quality_score": quality_score,
                    "combined_score": round(final_score * quality_score, 4),
                    "evidence_tier": evidence_tier,
                })

            if not passage_rows:
                continue

            passage_rows.sort(key=lambda row: row["combined_score"], reverse=True)
            documents.append({
                "source": ev["source"],
                "url": ev["url"],
                "weight": ev["weight"],
                "document_score": max(row["combined_score"] for row in passage_rows),
                "passages": passage_rows[:3],
            })

        documents.sort(key=lambda row: row["document_score"], reverse=True)
        selected_docs = documents[:4]
        selected_passages = []
        for doc in selected_docs:
            selected_passages.extend(doc["passages"][:2])
        selected_passages.sort(key=lambda row: row["combined_score"], reverse=True)
        return selected_passages[:6]
