# Unified Retrieval-First Improvement Plan

## Summary

This plan merges the retrieval and fine-tune roadmaps into one execution order.

Core rule:
- improve retrieval quality first
- fine-tune relevance next
- revisit stance only after evidence quality improves

Current promoted stack to preserve until a later benchmark win:
- claim type: `checkpoints/claim_type/latest`
- context: `checkpoints/context/latest`
- stance: `checkpoints/stance/v2_run1`
- relevance: `checkpoints/relevance/v2_run1`

## Ordered Phases

### Phase 1: Better Extraction and Observability
- upgrade extraction in scraper and webpage ingestion
- use `trafilatura` first and BeautifulSoup as fallback
- add retry, timeout, local extraction cache, and rejection logging

### Phase 2: Better Search and Candidate Ranking
- extend query generation using entities, years, claim type, and context
- add trusted-source search variants
- rank URLs before scraping using title overlap, year match, domain quality, and numeric hints
- log which query selected each URL

### Phase 3: Multi-Passage Evidence
- stop collapsing documents too early
- score multiple passages per source
- aggregate at document level before final verdict aggregation

### Phase 4: Claim-Type and Context-Aware Retrieval
- make retrieval ranking depend more on claim type and context
- strengthen India-local routing through state-specific source hints
- keep this as retrieval guidance only, never verdict logic

### Phase 5: Context Fine-Tuning for Retrieval Guidance
- expand context data with local/state and misinformation-sensitive examples
- retrain the context classifier
- keep low-confidence lexical fallback

### Phase 6: Relevance Fine-Tuning for Direct Answers
- use the cleaner manual seed set in `data/relevance/v5`
- expand only with high-signal manual pairs from live failures
- compare new checkpoints against `v2` on focused claims first

### Phase 7: Revisit Stance Fine-Tuning
- retrain stance only after retrieval and relevance improve
- build stance data from post-retrieval-improvement failures

### Phase 8: Local Trusted Corpus and FAISS
- build a local trusted passage corpus
- add embeddings and FAISS retrieval before live web search

### Phase 9: Continuous Corpus Growth
- save strong passages from successful runs
- deduplicate and refresh the local index over time

### Phase 10: Optional Browser Rendering Fallback
- add Playwright only for JS-heavy failures
- keep it limited, cached, and non-default

### Phase 11: Promotion, Benchmarking, and Cleanup
- benchmark after every major retrieval or model phase
- promote only if the live benchmark improves without raising dangerous false positives

## Test Plan

Focused validation after each major phase:
- `Climate change is a hoax`
- `The moon landing was faked`
- `Mars has two moons`
- `The Berlin Wall fell in 1989`
- `The United Nations was founded after World War II`
- `Humans can breathe in space without equipment`
- `Bananas are berries`
- `Octopuses have three hearts`

Full benchmark after each behavior-changing phase:
- `benchmark_multi_test.py`

Track:
- accuracy
- neutral rate
- false positive rate
- false negative rate
- `neutral_despite_evidence`
- `insufficient_evidence`
