# Retrieval and Relevance Execution Plan

Status: Execution-ready as of 2026-03-21

## Purpose

This plan is for improving the project toward its intended runtime behavior:

- real-time
- internet-first
- retrieval-led truth finding
- minimal heuristics in critical decision layers
- no promotion of new models without live benchmark evidence

This is not a generic research roadmap. It is an operational plan for the current repo state.

## Project Aim To Preserve

Non-negotiable runtime principles:

- Live internet retrieval remains the primary evidence path.
- Local models support ranking and classification; they do not become the primary source of truth.
- Heuristics may exist as narrow safety rails, but they must not grow into the main decision engine.
- Improvements should reduce brittle hand-tuned logic over time, not add more of it.
- Any change must be validated on live traces and benchmark outputs, not just by code inspection.

## Current Repo Reality

These facts matter before execution starts:

- `trafilatura` extraction is already integrated in `evidence/extraction_utils.py`.
- Search candidate scoring already exists in `evidence/router.py`, but it is still heuristic-heavy and does not yet include BM25-style lexical relevance.
- Trace visibility for scraped pages already includes `rank_score`, `word_count`, `extractor`, and rejection metadata.
- Multi-sentence selection and document-level consolidation already exist in `pipeline/claim_pipeline.py`, but they are not yet the clean, final form of a low-heuristic retrieval pipeline.
- Relevance v7 dataset artifacts and a `checkpoints/relevance/v7_run1` checkpoint already exist in the repo.
- The currently promoted relevance checkpoint remains `checkpoints/relevance/v2_run1`.

Because of that, this plan is written as:

- validate what already exists
- remove plan/code mismatches
- finish the highest-impact missing work
- promote only after live proof

## Global Promotion Rules

Use these rules for every promotion decision in this document:

- Full benchmark accuracy must not decrease.
- False-positive rate must not increase.
- Neutral rate should decrease.
- Focused failure claims must improve before full-benchmark promotion is allowed.
- If a change improves offline metrics but harms live internet behavior, do not promote it.

## Global Anti-Heuristic Rules

These constraints apply to every phase:

- Do not add new verdict heuristics to compensate for retrieval failures.
- Do not add domain-specific title rules unless a narrow safety case is documented.
- Prefer model-backed or trace-backed ranking signals over hand-authored keyword bonuses.
- If a heuristic is temporarily added, it must be trace-visible and easy to remove.
- Context and claim-type outputs may guide retrieval, but must not become direct verdict substitutes.

## Baseline To Record Before Any Phase Work

Before making phase changes, record one fresh baseline packet from the current promoted stack:

1. Run one focused claim set.
2. Run one mini benchmark batch.
3. Save trace artifacts for both.
4. Record:
   - benchmark accuracy
   - false-positive rate
   - neutral rate
   - average scraped pages per claim
   - average usable scraped pages per claim
   - average claim latency
   - evidence selection failures by category

Required output artifacts:

- tested claims list
- benchmark output JSON
- trace samples showing candidate ranking and scrape outcomes
- short written summary of the failure patterns observed

## Focused Validation Set

Use this set repeatedly before full benchmark runs:

- Climate change is a hoax
- The moon landing was faked
- Mars has two moons
- The Berlin Wall fell in 1989
- The United Nations was founded after World War II
- Humans can breathe in space without equipment

Add any current benchmark failures that are classified as:

- `neutral_despite_evidence`
- `insufficient_evidence`
- false positive with weak textual match

## Phase 1: Retrieval Honesty Baseline

Status: Ready to execute

### Goal

Make candidate retrieval and scraping behavior observable and trustworthy before changing model promotion.

### Why this phase comes first

The current system still risks ranking pages through a heuristic-heavy search candidate scorer. If the wrong pages are scraped, downstream relevance and stance changes will be misleading.

### Scope

- Keep internet-first retrieval.
- Do not train or promote models in this phase.
- Do not add new verdict heuristics.
- Focus only on retrieval, candidate ranking, scraping quality, and trace honesty.

### Work items

1. Run live trace collection on the focused claim set and one mini benchmark batch.
2. Verify per-URL scrape outputs for:
   - extractor used
   - word count
   - reject reason
   - whether the page body is usable and not boilerplate-heavy
3. Update documentation status to match reality:
   - `trafilatura` is already present
   - trace fields already exist
   - current gaps must be stated honestly
4. Add BM25-style lexical relevance to `_score_search_candidate()` in `evidence/router.py`.
5. Reweight candidate scoring so textual match becomes the primary ranking signal, while source quality and domain priors remain secondary modifiers.
6. Log candidate score components in trace output so each selected URL can be explained.
7. Reduce scrape fan-out only after ranking quality clearly improves.

### Phase 1 implementation target

Desired candidate score structure:

- primary: textual claim-to-candidate relevance
- secondary: source quality and domain reliability
- tertiary: narrow contextual bonuses
- penalties: low-signal or weak-result patterns

Undesired structure:

- domain authority dominating weak textual match
- claim-specific hand-authored title tricks becoming the main driver

### Completion checks

All must pass:

- Focused claims produce traces with visible candidate score components.
- Scrape traces show `extractor`, `word_count`, and `reject_reason` for the majority of attempted URLs.
- Most scraped pages for focused claims contain usable extracted text above the minimum threshold.
- Top-ranked URLs are textually aligned with the claim more often than under the current baseline.
- BM25-style relevance is visibly part of candidate scoring.

### Evidence to record

- before/after candidate ranking examples
- before/after scrape quality examples
- score component breakdown for selected URLs
- scrape fan-out counts before and after

### Do not advance if

- traces are incomplete or misleading
- ranking still depends mainly on authority/domain bonuses
- scrape quality remains poor on focused claims

## Phase 2: Relevance Audit, Residual Follow-up, and Provisional Handoff

Status: Deferred follow-up

### Goal

Decide whether the existing relevance v7 artifacts deserve promotion in the live internet-first pipeline.

### Why this phase is phrased this way

Relevance v7 is not greenfield work in this repo. Dataset artifacts and a checkpoint already exist. The job is to audit and validate them honestly.

### Scope

- Use existing v7 dataset and checkpoint as the candidate.
- Do not assume promotion just because the checkpoint already exists.
- Measure live direct-answer ranking behavior on focused claims first.

### Work items

1. Inspect `data/relevance/v7` and document:
   - train/validation/test counts
   - class balance
   - duplicate risk
   - source provenance mix
2. Inspect `checkpoints/relevance/v7_run1` and confirm it is runnable in isolation.
3. Run focused claims with promoted relevance baseline (`v2_run1`).
4. Run the same focused claims with relevance v7 enabled.
5. Compare whether direct-answer sentences rank above contextual/background sentences.
6. If focused behavior improves, run the full 30-claim benchmark.
7. Promote only if global promotion rules are satisfied.

### Completion checks

All must pass:

- v7 dataset provenance and balance are documented
- v7 checkpoint runs successfully in the current runtime
- focused failure claims show better direct-answer passage ranking than `v2_run1`
- full benchmark does not violate any promotion rule

### Evidence to record

- dataset counts and class ratios
- focused-claim ranking snapshots before and after
- benchmark delta against `v2_run1`
- explicit promotion or non-promotion decision

### Do not advance if

- focused claims still rank background/context above direct answers
- benchmark accuracy drops
- false positives rise
- improvements depend on offline behavior that does not show up in live retrieval runs

### Phase 2 handoff note

Phase 3 may begin provisionally with `v9_run1`, but this does not mean Phase 2 is solved. The open follow-up list remains:

- reduce `Amazon River` false-positive support bias
- reduce `bananas` neutral-despite-evidence failures
- revisit `v10` or later public-data candidates only if they beat `v9` on live residual behavior

### Current phase state

- `v7_run1` was evaluated and should not be promoted.
- `v8` remained too weak on the residual gate and was not promoted.
- `v9_run1` is the strongest recent candidate on the hard residual live set.
- `v9_run1` residual benchmark result: accuracy `0.75`, neutral rate `0.125`, false-positive rate `0.125`.
- `v9_run1` fixed multiple earlier residual failures, including `Lake Baikal`, `Roman Empire 476 AD`, and `Humans can breathe in space without equipment`.
- `v9_run1` still has two important residual issues: `Amazon River` false-positive support bias and `bananas` neutral-despite-evidence.
- `v11_run1` was a regression and should not be promoted.
- `v11_run1` residual benchmark result: accuracy `0.125`, neutral rate `0.875`, false-positive rate `0.0`.
- The `v11` cleanup/expansion attempt made the system broadly over-abstain, so it does not justify another immediate Phase 2 hold.
- A public-web import path exists for AVeriTeC-style JSON, but `v10` has not been adopted as the preferred next candidate.
- Because the project goal is minimal heuristics and forward progress matters, `v9_run1` is kept as the provisional experimental relevance checkpoint while broader Phase 2 refinement is deferred.
- The promoted stable baseline does not automatically change just because Phase 3 work begins.
- Recent multilingual Phase 5 fixes did not change this Phase 2 conclusion; `v9_run1` remains the best practical working relevance checkpoint.

### Why `v9` is kept for the next step

`v9_run1` is not treated as a final Phase 2 success. It is kept because it is the best live-tested relevance candidate among the recent residual follow-ups.

Decision logic:

- Keep `v9` because it materially improved the hard residual live set relative to `v8` and `v11`.
- Do not keep `v11` because it collapsed into broad `NEUTRAL` behavior on live claims.
- Do not block Phase 3 on perfect Phase 2 closure, because the remaining `v9` misses are narrow and already understood.
- Do not mark Phase 2 complete, because `Amazon` support bias and `bananas` abstention are still open relevance issues.

Operationally, this means:

- `v9_run1` is the relevance checkpoint to use for next-step experimental work.
- Phase 2 remains open as a deferred refinement track.
- Any future Phase 2 revisit should compare against `v9_run1`, not `v11_run1`.

### Public data path

Public internet-grounded data may be added in Phase 2 if it is handled with light cleaning only.

Allowed:

- keep original claims
- keep original labels
- keep original source URLs
- keep answer/evidence text mostly intact
- drop empty, duplicate, or unanswerable rows
- generate simple cross-claim negatives for relevance training

Not allowed:

- heavy manual rewriting
- claim-specific relabeling to force benchmark wins
- rule-heavy normalization that changes the character of the public dataset

## Phase 3: Passage Retention and Document-Level Aggregation Cleanup

Status: Sufficient for now, paused with deferred edge-case follow-up

### Goal

Make the already-partial multi-passage path cleaner, more consistent, and less heuristic-dependent before any stance retraining.

### Why this phase matters

The repo already retains multiple candidate sentences and performs document consolidation. The risk is not total absence; the risk is partial implementation with uneven weighting and too much reliance on early sentence or handcrafted bonuses.

### Scope

- Work inside the current internet-first claim pipeline.
- Preserve multiple strong passages per source where they are genuinely relevant.
- Improve document aggregation behavior without turning it into a heuristic maze.
- Use `v9_run1` as the working experimental relevance checkpoint for Phase 3 validation unless a later Phase 2 candidate clearly beats it live.

### Work items

1. Audit current passage selection in `pipeline/claim_pipeline.py`.
2. Measure how often later passages carry the decisive signal while early passages are weak or neutral.
3. Reduce dependence on positional and direct-answer handcrafted boosts where model-backed relevance already performs well.
4. Ensure multiple passages from the same document can survive into stance scoring when justified.
5. Tighten document-level aggregation so it reflects passage agreement cleanly and traceably.
6. Add or refine trace output for:
   - retained passages per document
   - dropped passages and why they were dropped
   - document-level consolidation decisions

### Completion checks

All must pass:

- multiple passages are retained for at least some focused claims with long-form evidence
- document-level aggregation is clearly trace-visible
- known `neutral_despite_evidence` cases improve because later strong passages are preserved
- passage handling is simpler or more principled after the change, not more heuristic-heavy

### Current phase state

- Phase 3 work has already started and produced live benchmark evidence.
- Document-level consolidation is now trace-visible.
- Same-document passage survival is improved enough to be observable in runtime behavior.
- Full-stack comparison runs were completed across baseline and experimental env combinations.
- The remaining hard misses in the best-performing stack are not a single clean Phase 3 issue:
  - `5G networks spread coronavirus` includes stance/logic interaction risk
  - `The Great Wall of China is visible from space` is partly an ambiguity/definition case
  - `The Amazon River is the longest river in the world` is partly a disputed-comparison case
- Because of that, Phase 3 should not keep expanding unless a clearly non-heuristic, general fix appears.
- The current recommendation is to pause Phase 3 here and carry the remaining false positives as deferred cleanup, not as a blocker to Phase 4.
- Later multilingual Phase 5 fixes built successfully on this Phase 3 structure and did not expose a new passage-retention or document-collapse reason to reopen broad Phase 3 work.

### Evidence to record

- before/after retained-passage counts
- one concrete claim where document-level consolidation changed the outcome
- focused delta on `neutral_despite_evidence` style failures

### Do not advance if

- most documents still effectively collapse to one sentence too early
- the cleanup adds more hand-tuned rules than it removes
- document-level aggregation exists in code but not in meaningful runtime behavior

## Phase 4: Session-Scoped Retrieval Cache

Status: Active, validated, and tuned for near-paraphrase reuse

### Goal

Reduce repeated scraping and improve latency for repeated or highly similar claims, without violating the internet-first runtime principle.

### Scope

- Cache is supplementary only.
- Live retrieval must still execute on every claim.
- Cache must never become the primary fact-check source.

### Work items

1. Define a strict quality gate for cache insertion.
2. Store only strong, high-quality, high-relevance passages with source metadata.
3. Query the cache at the start of each claim as a supplement.
4. Keep live search and scraping active even when cache hits exist.
5. Measure:
   - cache hit rate
   - scrape reduction
   - latency change
   - noise injection risk

### Completion checks

All must pass:

- cache hits are supplementary only
- live retrieval still runs on every request
- repeated-claim latency improves
- benchmark quality does not regress

### Current phase state

- A supplementary session-scoped retrieval cache is now implemented.
- The cache stores only strong, high-quality passages with source metadata.
- Live retrieval still executes on every tested repeated claim.
- Cache lookup and store behavior are now trace-visible in pipeline transparency.
- Repeated-claim validation artifact: `logs/phase4_repeat_claim_validation.json`
- Similar-claim validation artifacts:
  - `logs/phase4_similar_claim_validation.json`
  - `logs/phase4_similar_claim_validation_post_tuning.json`
- Broader repeated-query validation artifact:
  - `logs/phase4_broader_repeat_query_validation.json`
- Validation summary:
  - average first pass: `63.804s`
  - average second pass: `1.694s`
  - average improvement: `62.11s`
- Similar-claim summary after one tuning pass:
  - matched pairs: `3/4`
  - returned pairs: `3/4`
  - appended pairs: `2/4`
- Broader repeated-query summary:
  - claim count: `10`
  - verdict stability: `10/10`
  - average first pass: `85.094s`
  - average second pass: `1.410s`
  - average improvement: `83.684s`
  - second-pass matched claims: `9/10`
  - second-pass returned claims: `9/10`
  - second-pass appended claims: `0/10`
- The current validation confirms the architectural requirement, but not yet the full Phase 4 completion condition:
  - the cache is supplementary
  - live retrieval still runs
  - repeated-claim latency improves
  - near-paraphrase reuse now works better after tuning
  - broader regression validation on the full benchmark is still pending

### Evidence to record

- insertion counts
- hit-rate stats
- repeated-claim latency examples
- proof that live retrieval still executed

### Do not advance if

- cache starts replacing live retrieval behavior
- similarity thresholds are loose enough to inject irrelevant evidence

## Phase 5: Stance Retraining On Residual Failures Only

Status: In progress as residual semantic hardening; retraining still gated

### Goal

Use post-Phase-4 residuals to separate:

- semantic/relation failures that can be cleaned up without retraining
- multilingual/local-language failures caused by routing or post-translation interpretation
- genuine stance-model failures that would justify a later training round

### Why this phase is last

Many apparent stance problems are actually retrieval or evidence-selection problems. Training stance on noisy residuals would move the project away from the intended architecture.

### Scope

- Use post-Phase-4 live failures only.
- Exclude failures fixed by retrieval, relevance, passage-selection, cache, or semantic postfilter improvements.
- Keep the real-time internet-first runtime as the evaluation target.
- For multilingual deployment, preserve original-language retrieval and evaluate post-translation semantic behavior explicitly.

### Work items

1. Re-run focused claims and multilingual residual claims after Phases 1 through 4.
2. Label remaining failures by root cause:
   - retrieval failure
   - relevance/ranking failure
   - passage retention failure
   - multilingual semantic/relation failure
   - genuine stance decision failure
3. Apply narrow semantic fixes first where the failure is clearly post-translation relation handling rather than model ignorance.
4. Build stance seeds only from genuine stance failures that remain after the semantic cleanup pass.
5. Train and compare against the currently promoted stance checkpoint only if that clean seed set is large enough to justify it.
6. Promote only if benchmark evidence is clearly positive and false-positive risk does not rise.

### Completion checks

All must pass:

- residual failures are root-caused in writing
- multilingual semantic failures are separated from pure stance failures
- stance training data excludes retrieval-origin and relation-origin noise
- any candidate stance model improves live benchmark behavior
- false-positive risk does not worsen

### Evidence to record

- residual failure taxonomy
- multilingual residual benchmark and retry notes
- stance seed provenance summary
- benchmark delta and promotion decision

### Current phase state

- Phase 5 is active as semantic hardening, not stance retraining.
- Benchmark reruns now self-label `valid` vs `invalid_search_collapsed`.
- Search/provider backoff now short-circuits obviously invalid collapsed-network runs.
- `phase5_multilingual_compare.py` now compares new multilingual reruns directly against the trustworthy `fix2` baseline.
- A valid multilingual improvement run now exists:
  - artifact: `logs/multilingual_regression_batch_v2_results_retry4.json`
  - accuracy `0.8`
  - false-positive rate `0.0`
  - neutral rate `0.2`
- Relative to the trustworthy multilingual `fix2` baseline, this improved:
  - accuracy `0.6 -> 0.8`
  - false-positive rate `0.2 -> 0.0`
  - neutral rate `0.2 -> 0.2`

Important claim-level changes:

- `Mumbai is the capital of India` moved from wrong `TRUE` to correct
- Tamil `Bengaluru is the capital of India` moved from `NEUTRAL` to correct
- Kannada `Bengaluru is the capital of India` moved from `NEUTRAL` to correct
- Telugu AP farmer alert moved from unsafe `TRUE` to safer `NEUTRAL`

Current interpretation:

- Phase 5 is now producing real multilingual safety gains
- the remaining multilingual issues are no longer dominated by unsafe false positives
- this is still not enough reason to open a new stance-training loop

### Do not advance if

- stance training data still contains unresolved retrieval or relation noise
- multilingual residuals are still dominated by routing or semantic contradictions that do not require retraining
- the new stance model only looks better offline
- live benchmark behavior becomes less reliable

## What Counts As Success

This plan succeeds if, by the end:

- the system remains real-time and internet-first
- retrieval ranking is primarily driven by actual claim-text relevance
- scrape quality is observable and mostly usable
- direct-answer evidence is surfaced more reliably
- neutral-despite-evidence cases fall
- false-positive risk does not rise
- the runtime depends less on brittle handcrafted rules than it does today

This plan fails if the project gains accuracy only by adding more ad hoc heuristics, special-case title rules, or local-first shortcuts that move it away from the intended architecture.

## Execution Order

Strict order:

1. Baseline packet
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5

No reordering unless a blocking reason is documented in writing.

## Immediate Next Step

Reassess whether Phase 2 or Phase 3 actually need reopening before pushing Phase 5 further.

Use the current valid multilingual improvement run as the decision input:

- if remaining failures now point back to relevance quality, reopen Phase 2 narrowly
- if remaining failures now point back to document collapse or aggregation, reopen Phase 3 narrowly
- otherwise, keep Phase 5 as targeted semantic hardening and do not open stance training yet
