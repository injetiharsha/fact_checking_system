# Fine-Tune Phased Plan

## Summary

This plan covers only model and dataset improvement work, separate from the evidence-retrieval roadmap.

Current status:
- claim type: trained and usable
- context classifier: trained and usable as soft routing metadata
- stance: `v2` remains the promoted runtime checkpoint
- relevance: `v2` remains the promoted runtime checkpoint
- newer stance/relevance experiments improved some offline or focused behavior, but have not yet beaten the promoted stack cleanly in full benchmark runs

Default strategy:
- retrieval work is handled in `EVIDENCE_RETRIEVAL_PHASED_PLAN.md`
- this plan assumes retrieval improves in parallel or first
- do not promote any new model unless it beats the current promoted model on both offline metrics and targeted live benchmark checks

## Phase Breakdown

### Phase 1: Freeze Current Promoted Baseline
Status: `Completed`

Baseline currently treated as promoted:
- claim type: `checkpoints/claim_type/latest`
- context: `checkpoints/context/latest` as soft metadata only
- stance: `checkpoints/stance/v2_run1`
- relevance: `checkpoints/relevance/v2_run1`

Completion state:
- benchmark baseline exists in `parallel_test_results.json`
- transparency and routing outputs are visible enough for comparison
- current promoted checkpoints are known

### Phase 2: Claim Type Stabilization
Status: `Completed`

Purpose:
- make claim type usable without being the main source of regression

Delivered state:
- trained checkpoint exists
- fallback path still exists for low-confidence cases
- current benchmark evidence shows claim type is no longer the main bottleneck

Promotion rule already satisfied for practical use:
- safe runtime behavior
- no strong sign that more claim-type tuning is the best next lever

### Phase 3: Context Classification for Retrieval Guidance
Status: `In Progress`

Purpose:
- provide domain, subcategory, risk flags, and India-local state hints for retrieval guidance
- keep context model out of verdict logic

Current delivered state:
- taxonomy exists
- trained context checkpoint exists
- runtime can use trained context through feature flag with safe lexical fallback
- context is already exposed in transparency and used for soft search-query shaping

Remaining work before this phase is truly complete:
- expand context dataset with more local/state and misinformation-sensitive examples
- improve test accuracy beyond the current prototype level
- validate that context-guided routing measurably improves evidence quality on focused retrieval checks

Completion checks:
- held-out context accuracy is strong enough for routing use
- focused retrieval runs show better sources or query plans on domain-heavy claims
- India-local claims surface better local candidates consistently

### Phase 4: Stance Failure-Driven Fine-Tuning
Status: `Partially Completed`

Purpose:
- improve support/refute/neutral prediction on benchmark-style evidence

Current delivered state:
- `v2`, `v3`, `v4`, and `v5` have been trained
- `v5` is the strongest offline stance checkpoint so far
- but `v5` did not clearly beat `v2` in full benchmark behavior
- `v2` remains promoted

Next stance tuning rule:
- do not start `stance v6` yet
- only resume stance fine-tuning after retrieval quality or relevance quality improves
- future stance datasets should come from post-retrieval-improvement failures, not current noisy evidence alone

Completion checks for next stance promotion:
- full benchmark accuracy improves over the `v2` stack
- false positives do not rise
- neutral rate drops materially
- targeted hard claims improve live, not just offline

### Phase 5: Relevance Direct-Answer Fine-Tuning
Status: `In Progress`

Purpose:
- train the reranker to prefer direct factual answer sentences over merely related or background sentences

Current delivered state:
- `relevance v2` is still the promoted checkpoint
- `relevance v3` underperformed and was rejected
- `relevance v4` was trained on broader hard failures but underperformed `v2`
- a cleaner manual seed set now exists as `data/relevance/v5`

Next implementation direction:
- use `v5` as the next fine-tune seed
- keep it high-signal and manual-first
- avoid reintroducing large noisy auto-generated negatives until the manual seed performs well
- compare `v5` against `v2` on focused hard claims before any full promotion decision

Completion checks:
- `v5` beats `v2` on offline validation and test, or at minimum holds close offline while clearly improving focused live claim behavior
- focused claims improve:
  - climate misinformation
  - moon landing misinformation
  - direct factual history claims
  - direct factual space/science claims
- no regression on already-good claims like `Bananas are berries` and `Octopuses have three hearts`

### Phase 6: Promotion, Benchmarking, and Cleanup
Status: `Not Started`

Purpose:
- promote only checkpoints that improve end-to-end behavior
- keep the repo clean and checkpoint sprawl controlled

Tasks:
- benchmark any new promoted candidate against the current promoted stack
- compare offline metrics and live benchmark metrics together
- keep only promoted and comparison checkpoints
- reject checkpoints that improve offline metrics but worsen end-to-end benchmark precision or false positives

Completion checks:
- benchmark comparison recorded
- promotion or rejection decision documented
- stale checkpoint snapshots cleaned after successful reruns

## Test Plan

### Focused model validation
Run these before any promotion:
- `Climate change is a hoax`
- `The moon landing was faked`
- `Mars has two moons`
- `The Berlin Wall fell in 1989`
- `The United Nations was founded after World War II`
- `Humans can breathe in space without equipment`

### Full benchmark validation
Run:
- `benchmark_multi_test.py`

Track:
- accuracy
- neutral rate
- false positive rate
- false negative rate
- `neutral_despite_evidence`
- `insufficient_evidence`

### Promotion acceptance criteria
A checkpoint is promotable only if:
- it beats or clearly improves on the current promoted stack in full benchmark behavior
- it does not increase dangerous false positives
- it improves live evidence handling for targeted failure claims

## Assumptions and Defaults

- Retrieval remains the current main bottleneck, so retrieval work should happen before major new stance tuning.
- The current promoted fine-tune stack is:
  - claim type: `latest`
  - context: `latest` for soft routing only
  - stance: `v2_run1`
  - relevance: `v2_run1`
- The next best fine-tune experiment is `relevance v5`, not `stance v6`.
- Context remains retrieval-only guidance and should not influence verdict logic directly.
- Manual high-signal examples are preferred over broader noisy auto-generated examples for the next relevance iteration.
