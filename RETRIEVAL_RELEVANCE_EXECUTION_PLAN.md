# Retrieval and Relevance Execution Plan (Internet-First, Honest Pipeline)

## Why this plan exists

This plan enforces one rule: do not optimize downstream models until retrieval quality is verified with real traces.

Current baseline assumptions:
- Runtime mode remains internet-first.
- Claim type checkpoint remains unchanged unless new evidence shows it is a bottleneck.
- Existing promoted stack remains active until explicit promotion gates are met.

Promotion gates used throughout this plan:
- Full-benchmark accuracy must not drop.
- False-positive rate must not rise.
- Neutral rate should fall.

---

## Phase 1: Retrieval Honesty Baseline (Extraction + Candidate Ranking)

Status: Not Started

### Objective
Make the current retrieval layer trustworthy before any new model promotion:
- Confirm extraction quality on real claims using trace outputs.
- Add BM25 relevance to pre-scrape candidate ranking in router scoring.

### Scope
- Verify real behavior, not only code comments or plan text.
- Keep internet-first retrieval.
- Do not train models in this phase.

### Tasks
1. Run real claims through the live pipeline and collect trace outputs.
2. For each selected URL, verify extracted article body quality:
- clean body text (not nav/footer boilerplate)
- extracted word count > 100 for usable pages
- extraction method recorded in trace
3. Reconcile documentation mismatch:
- plan files currently say trafilatura integration is pending
- code already shows trafilatura integration in extraction utilities
- update plan status based on observed runtime traces
4. Add BM25 scoring to router candidate scoring in [evidence/router.py](evidence/router.py):
- integrate BM25 claim-to-candidate textual relevance in _score_search_candidate()
- keep existing quality/domain signals as secondary features
- log score components per URL in trace/debug outputs
5. Re-rank and reduce scrape fan-out using combined score:
- ensure top scraped URLs are textually relevant, not only high-authority domains

### Completion checks (all required)
- At least one focused claim batch and one benchmark mini-run produce traces with extraction method and word-count visibility.
- Usable extracted pages (clean body, >100 words) are the majority of scraped pages for focused test claims.
- BM25 component is present in candidate scoring and visible in logs/traces.
- Selected top URLs show improved textual relevance to the claim compared with pre-change behavior.

### Evidence to record before phase completion
- List of tested claims.
- Before/after URL ranking examples.
- Before/after extracted word-count summary.
- File changes and scoring formula summary.

### Do not advance if
- Traces still show frequent low-text or boilerplate extraction.
- Ranking remains dominated by domain authority when textual match is weak.

---

## Phase 2: Relevance v7 Training and Promotion Decision

Status: Not Started

### Objective
Train relevance v7 from existing internet-backed seeds and promote only if focused and full-gate checks pass.

### Scope
- Use existing relevance v7 dataset builder and training pipeline.
- Validate direct-answer sentence ranking behavior on known neutral failures.

### Tasks
1. Build relevance v7 dataset from current builder.
2. Inspect class balance and source distribution:
- positive/negative ratio
- seed provenance and duplicates
3. Train relevance model using the existing relevance training config, pointed to v7 data.
4. Run focused neutral-failure claims first.
5. Confirm direct-answer evidence sentences score above relevance threshold and rank above background/context sentences.
6. Only then run full 30-claim benchmark.
7. Apply unchanged promotion gates:
- accuracy not lower
- false-positive rate not higher
- neutral rate lower

### Completion checks (all required)
- Dataset built successfully with expected train/validation/test files.
- Class distribution is acceptable and documented.
- Focused failure set shows direct-answer ranking improvement over promoted baseline.
- Full benchmark satisfies promotion gates.

### Evidence to record before phase completion
- Dataset counts and class balance.
- Focused-claim before/after relevance ranking snapshots.
- Full benchmark delta against promoted baseline.

### Do not advance if
- Focused claims still rank background sentences above direct answers.
- Full benchmark fails any promotion gate.

---

## Phase 3: Multi-Passage Evidence and Document-Level Aggregation

Status: Not Started

### Objective
Remove early single-sentence collapse behavior by scoring and aggregating multiple passages per document before final verdict aggregation.

### Why this phase is after Phase 2
Relevance v7 should first improve passage quality; then multi-passage aggregation can combine stronger candidates effectively.

### Scope
- Update evidence processing in [pipeline/claim_pipeline.py](pipeline/claim_pipeline.py).
- Keep multiple passages per source through stance stage.
- Add document-level aggregation before global verdict aggregation.

### Tasks
1. Preserve multiple candidate passages per source (not just early single best).
2. Run stance detection per selected passage.
3. Aggregate stance/evidence signal at document level first:
- produce per-document support/refute/neutral summary
- carry confidence and quality weights forward
4. Feed document-level outputs into final weighted verdict aggregation.
5. Add trace visibility for passage and document aggregation decisions.

### Completion checks (all required)
- At least some claims process more than one passage per source through stance.
- Document-level aggregation exists and is used before final global aggregation.
- Known cases with weak leading sentence and strong later sentence show improved outcomes.

### Evidence to record before phase completion
- Number of passages retained per source (before/after).
- One concrete claim where document-level aggregation changed the selected evidence path.
- Benchmark/focused delta for neutral-despite-evidence style failures.

### Do not advance if
- Pipeline still collapses to one sentence before stance for most sources.
- Document-level signals are computed but not used in final aggregation.

---

## Phase 4: Session-Scoped FAISS Embedding Cache (Supplementary Only)

Status: Not Started

### Objective
Reduce redundant scraping within a server session by adding a lightweight in-memory FAISS cache of strong passages.

### Non-negotiable behavior
- Live search always runs.
- Cache never replaces live internet retrieval.
- Cache returns supplementary evidence only.

### Scope
- Add a session-scoped FAISS index for high-quality passages.
- Use tight cosine threshold for cache hits.
- Keep lifecycle in-memory per server process/session.

### Tasks
1. Define quality gate for cache insertions (only strong passages).
2. Embed and store qualified passages with metadata.
3. On each claim, query cache first for high-similarity passages.
4. Return cache hits as supplementary evidence while still executing live retrieval pipeline.
5. Track cache hit rate and benchmark time savings.

### Completion checks (all required)
- Cache stores only passages above quality threshold.
- Cache lookups occur per claim with strict similarity threshold.
- Live retrieval still executes on every claim.
- Benchmarks show reduced repeated scraping and lower latency for repeated patterns.

### Evidence to record before phase completion
- Cache insertion counts and hit-rate stats.
- One repeated-claim example showing latency or scrape-count reduction.
- Verification that live retrieval path still ran.

### Do not advance if
- Cache is used as a retrieval replacement.
- Similarity threshold is loose enough to inject noisy passages.

---

## Phase 5: Stance Retraining from Post-Retrieval Residual Failures

Status: Not Started

### Objective
Train stance v4 only on genuine residual stance failures that remain after phases 1 through 3.

### Why this phase is last
Many apparent stance errors are retrieval-quality errors. Retrain stance only after evidence quality and passage selection are fixed.

### Scope
- Build training seed from remaining failures after retrieval/relevance/multi-passage improvements.
- Exclude failures resolved by retrieval fixes.

### Tasks
1. Re-run focused set and full benchmark after phases 1 through 3.
2. Label residual failures by cause:
- retrieval still weak
- relevance ranking weak
- genuine stance decision weakness
3. Build stance v4 seed only from genuine stance weaknesses.
4. Train and compare against promoted stance baseline.
5. Promote only if gates are met and no regression appears.

### Completion checks (all required)
- Residual failure sheet is cause-labeled.
- Stance seed excludes resolved retrieval-origin failures.
- Stance v4 shows benchmark improvement without increasing dangerous false positives.

### Evidence to record before phase completion
- Residual failure taxonomy.
- Stance v4 training-set provenance summary.
- Benchmark delta and promotion decision.

### Do not advance if
- Training set is still dominated by retrieval-origin noise.
- Stance model appears to improve only offline while live benchmark worsens.

---

## Claim Type Policy (Explicitly Out of Scope)

Claim type retraining is intentionally excluded from this plan.

Current policy:
- Keep current promoted claim type checkpoint unchanged.
- Revisit claim type only if transparency outputs after Phase 2 show frequent low-confidence claim-type decisions on failed claims.

Revisit trigger:
- repeated low-confidence claim-type decisions correlate with benchmark failures.

No trigger means no claim-type retraining.

---

## Execution Order (Strict)

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 5

No skipping and no reordering unless a phase is explicitly blocked and documented.

---

## Suggested Focused Claim Set for Repeated Validation

- Climate change is a hoax
- The moon landing was faked
- Mars has two moons
- The Berlin Wall fell in 1989
- The United Nations was founded after World War II
- Humans can breathe in space without equipment

Use these before full benchmark runs to check whether direct-answer evidence is selected and scored correctly.
