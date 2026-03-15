# Phased Roadmap (Heuristic Reduction)

This document captures the **latest phased plan** for reducing heuristic fallbacks in the fact-checking pipeline, **where we are today**, and **what comes next**.

---

## ✅ Current Status (Where we are)

- The system currently reports a transparency version of **`phase6-v1`** (see `pipeline/claim_pipeline.py`).
- This indicates we have completed **Phase 6**, which includes:
  - A full end-to-end pipeline with:
    - claim normalization and language detection
    - claim type classification (with model + heuristic fallback)
    - evidence retrieval, cleaning, and scoring (relevance + quality)
    - stance detection (NLI model + heuristic rescue steps)
    - logic engine reasoning + conflict analysis
    - verdict aggregation + transparency metadata
  - The first set of **phased heuristic reduction steps** (branch `feat/reduce-heuristics-phased`):
    - Heuristic rescue paths still exist, but are now clearly labeled (e.g., `heuristic_year_rescue`, `heuristic_rank_rescue`).
    - The system tracks the decision source in outputs so we can determine when heuristics are being applied.

---

## 📌 Phase Breakdown (What has been delivered)

### Phase 1 — Baseline heuristic system
- Claim type classification based on hard-coded keyword markers.
- Stance/claim evaluation driven by simple heuristics and rule-based signals.

### Phase 2 — Cached model augmentation
- Add local cached models (DistilBERT, NLI) for claim type and stance.
- Keep heuristics as fallback when models are missing or uncertain.

### Phase 3 — Trained model support + confidence gating
- Add trained model checkpoint support (isolated subprocess inference).
- Introduce confidence thresholds (e.g., `MODEL_CONFIDENCE_THRESHOLD` in `claim_type_classifier.py`).
- Fall back to heuristics when model confidence is low or output is invalid.

### Phase 4 — Evidence selection & filtering
- Introduce sentence extraction scoring, domain diversity filtering, and credibility thresholds.
- Improve evidence retrieval cleaning to avoid weak/irrelevant text.

### Phase 5 — Reasoning and verdict aggregation
- Add logic engine reasoning for structured verdict injection.
- Add conflict analysis and stronger verdict-aggregation rules.
- Introduce configurable thresholds for "strong" vs "soft" evidence.

### Phase 6 — Versioned transparency + phased heuristic reduction
- Introduced `transparency.version = "phase6-v1"` in pipeline output.
- Heuristics are still present but are now explicitly marked and tracked.
- This phase is the baseline for the current branch (`feat/reduce-heuristics-phased`).

---

## 🔭 What Comes Next (Phase 7+)

### Phase 7 — Retrieval coverage improvement (next step)
- **Goal:** Resolve the 6 insufficient-evidence benchmark failures by improving evidence availability, not by adjusting verdict heuristics.
- **Actions:**
  - Analyze the 6 insufficient-evidence failures and identify which sources or evidence types are missing.
  - Expand reference/backfill coverage in retrieval paths (trusted sources, fallback references, and retrieval routing).
  - Improve retrieval recall for low-coverage claims before any verdict logic changes.
  - Track a focused metric: insufficient-evidence count on benchmark should decrease without heuristic verdict overrides.

### Phase 8 — Stance v4 targeted retraining from benchmark failures
- **Goal:** Improve stance quality using failure-driven retraining data from benchmark misses.
- **Actions:**
  - Build a targeted training set from benchmark failures (especially disagreement/low-confidence stance outputs).
  - Retrain and evaluate stance v4 with error-category coverage (temporal, comparative, negation, ranking).
  - Validate gains against the benchmark and verify no regression in already-correct claims.
  - Promote v4 only after benchmark delta is positive and stable across multiple runs.

---

## 📌 Where the Plan Came From

- The current plan is derived directly from the codebase and the active branch:
  - `pipeline/claim_pipeline.py` sets `transparency.version = "phase6-v1"`.
  - Heuristic signals in `claim_detection/claim_type_classifier.py` and `semantic/stance_model.py` demonstrate the patterns we are reducing.
- The branch name `feat/reduce-heuristics-phased` reflects this multi-phase, incremental approach.

---

## ✅ Notes / Next Actions You Might Take

- Start with a failure sheet for the 6 insufficient-evidence claims: missing source type, query gap, and expected evidence pattern.
- Prioritize retrieval/backfill expansion first, then run benchmark again before starting stance v4 retraining.
- Use the updated benchmark failures as the seed set for stance v4 targeted retraining and ablation checks.
