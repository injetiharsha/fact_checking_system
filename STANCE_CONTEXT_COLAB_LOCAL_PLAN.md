# Stance-First Colab Local-First Plan

Status: draft execution plan as of 2026-04-07

## Goal

Use Colab GPU for stance training first, while keeping dataset ownership and final model artifacts local.

Context is a different model/task and is intentionally deferred to Phase 2.

Rules:
- Data source of truth stays in local repo or local export bundles.
- Train in Colab runtime GPU.
- Save final model once per run (plus optional one mid-run safety backup).
- Download checkpoint zip to local machine and place into local checkpoints folder.

## Current Runtime Checkpoints

Stance:
- checkpoints/stance/stage2_hardcases_v3_bias_restorefast_patch2

Context (deferred):
- checkpoints/context/latest

Reference stack:
- BEST_STACKS.md
- ARCHITECTURE_LOCK.md

## Checkpoint Roadmap (Stance)

1) Current promoted
- Name: stage2_hardcases_v3_bias_restorefast_patch2
- Purpose: stable production baseline
- Data already covered: hardcases plus multilingual residual corrections

2) Missing checkpoint A (planned)
- Target name: public_h2_multilingual_v2
- Purpose: broad multilingual generalization from public data
- Data required:
  - Multilingual stance pairs from public fact-check corpora
  - Balanced SUPPORT/REFUTE/NEUTRAL labels
  - Language mix with Telugu/Hindi/Tamil plus English
  - Deduplicated URL/text pairs
  - Split files: train/val/test with domain holdout

3) Missing checkpoint B (planned)
- Target name: hardcases_residual_v2
- Purpose: fix residual false positives and high-confidence neutral drift
- Data required:
  - Error-driven packet from latest benchmark logs
  - Short-claim vs long-claim contrast pairs
  - Contradiction-heavy regional claims
  - Annotation fields: claim, evidence, stance, language, source_quality

## Context Track (Deferred To Phase 2)

1) Current runtime
- Name: checkpoints/context/latest
- Purpose: retrieval guidance only (not verdict decision)

2) Missing checkpoint A (planned)
- Target name: context_public_h2_multilingual_v2
- Purpose: better domain/subcategory routing across multilingual claims
- Data required:
  - Domain labels aligned to claim_detection/context_taxonomy.py
  - Multilingual claim text with original language retained
  - Region hints and state_focus labels for India routing
  - Train/val/test splits with domain-stratified sampling

3) Missing checkpoint B (planned)
- Target name: context_residual_hardcases_v2
- Purpose: improve low-confidence fallback and reduce no_context_model_available events
- Data required:
  - Runtime traces where context confidence < 0.60
  - Misrouted retrieval examples from pipeline_trace.json
  - Corrected labels for domain, subcategory, risk_flags, query_language

## Phase 1: Stance Execution Workflow (Local-First)

1) Prepare local stance data bundle
- Export stance datasets into versioned folders under training/data_exports/stance/
- Include manifest.json with counts by label and language

2) Upload to Colab
- Option A: mount Google Drive and copy local bundle once
- Option B: upload zipped local bundle directly to /content

3) Train with minimal checkpoint churn
- Set save strategy to epoch or end
- Keep save_total_limit=1 (or 2 max)
- Keep one optional mid-run backup only for long jobs

4) Save final stance artifacts
- Ensure final directory contains tokenizer + model + config + label map
- Zip final output in Colab
- Download zip to local machine

5) Install locally
- Unzip to local target:
  - checkpoints/stance/<target_name>
- Update .env for evaluation run only (do not overwrite promoted baseline permanently)

6) Verify before promotion
- Run benchmark packet(s)
- Compare against BEST_STACKS baseline metrics
- Promote only if it beats baseline on accuracy and does not regress false-positive behavior

## Runtime Env Templates (Phase 1)

Stance candidate eval:

ENABLE_TRAINED_STANCE=1
STANCE_CHECKPOINT=checkpoints/stance/public_h2_multilingual_v2

Context candidate eval is deferred to Phase 2.

## Promotion Gate

Promote only if all are true:
- Better or equal overall accuracy vs current promoted stack
- No false-positive blow-up
- Multilingual slice improves or holds
- Latency does not regress materially in image and text flows

## Immediate Next Actions (Do Now)

1) Freeze local export schema for stance dataset only.
2) Build missing checkpoint A for stance in Colab.
3) Run local benchmark comparison and decide stance promotion.
4) Start context planning only after stance checkpoint decision.
