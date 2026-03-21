# Phase 5 Residual Taxonomy

Status: analysis-only Phase 5 entry note as of 2026-03-22

This document records the residual failures from the current best experimental stack and classifies them by likely root cause.

Purpose:

- decide whether Phase 5 should become actual stance retraining
- avoid training stance on failures that are really caused by retrieval, ambiguity, or runtime logic
- preserve the project aim of minimal heuristics and internet-first fact-checking

Reference stack used for this taxonomy:

- `ENABLE_TRAINED_STANCE=1`
- `STANCE_CHECKPOINT=checkpoints/stance/v2_run1`
- `ENABLE_TRAINED_RELEVANCE=1`
- `RELEVANCE_CHECKPOINT=checkpoints/relevance/v9_run1`
- `ENABLE_RETRIEVAL_V2=1`
- `ENABLE_VERIFIER_V2=1`
- `ENABLE_LLM_VERIFIER=1`
- `LLM_VERIFIER_POLICY=neutral_only`

Reference benchmark artifact:

- `logs/full_stack_benchmarks_2026-03-22_002140/combined_experimental_v9_rv2_vv2.json`

## Residual Failure Set

Current remaining misses from the best benchmark stack:

1. `5G networks spread coronavirus`
2. `The Great Wall of China is visible from space`
3. `The Amazon River is the longest river in the world`
4. `Humans share about 50 percent of their DNA with bananas`

## Root-Cause Taxonomy

Use these categories for Phase 5 gating:

- `runtime_logic_issue`
- `ambiguity_or_definition_issue`
- `retrieval_or_relevance_issue`
- `passage_strength_or_threshold_issue`
- `genuine_stance_model_issue`

Only the last category should directly feed a new stance-training round.

## Claim-By-Claim Classification

### 1. 5G networks spread coronavirus

Expected: `FALSE`  
Predicted: `TRUE`

Observed evidence pattern:

- one strong refuting BBC passage:
  - `There's absolutely no way 5G mobile phone signals either transmit the virus...`
- one GOV.UK sentence that should function as refutation:
  - `Coronavirus is also spreading in many countries that do not have 5G mobile networks.`
- one injected `logic_engine` support signal

Why this is not a clean stance-training case:

- the GOV.UK sentence is being treated as `SUPPORT` even though its meaning contradicts the claim
- a `logic_engine` support item is also present
- that means the error is not just “stance model failed on good evidence”

Primary classification:

- `runtime_logic_issue`

Secondary classification:

- `genuine_stance_model_issue` only as a possible sub-component

Phase 5 decision:

- do not use this as pure stance-training seed without first separating the runtime-logic problem

### 2. The Great Wall of China is visible from space

Expected: `FALSE`  
Predicted: `TRUE`

Observed evidence pattern:

- one passage explicitly saying it is not visible to the naked eye from space
- one passage saying visibility from low Earth orbit is possible under favorable conditions
- one NASA image-related support item

Why this is not a clean stance-training case:

- the claim is ambiguous:
  - “space” can mean low Earth orbit or much farther out
  - “visible” can mean naked eye or camera-assisted/photo-confirmed
- retrieved evidence is semantically mixed in ways that are not just support vs refute labels

Primary classification:

- `ambiguity_or_definition_issue`

Phase 5 decision:

- do not use this as a straightforward stance-training seed

### 3. The Amazon River is the longest river in the world

Expected: `FALSE`  
Predicted: `TRUE`

Observed evidence pattern:

- one support sentence explicitly saying Amazon is longest
- one sentence explicitly saying Nile is longest
- one debate-oriented sentence
- one injected `logic_engine` support signal

Why this is not a clean stance-training case:

- the evidence set mixes disputed-comparison sources
- the pipeline is not handling the conflict as a clean contradiction set
- one contradictory sentence is still ending up on the support side overall

Primary classification:

- `ambiguity_or_definition_issue`

Secondary classification:

- `runtime_logic_issue`

Phase 5 decision:

- do not use this as a pure stance-training seed

### 4. Humans share about 50 percent of their DNA with bananas

Expected: `TRUE`  
Predicted: `NEUTRAL`

Observed evidence pattern:

- one supporting passage survives:
  - `Primary Source: Do People and Bananas Really Share 50 Percent of the Same DNA?`
- surviving support item has modest weight and low quality
- final verdict stays `NEUTRAL`

Why this is closer to Phase 5 but still not a clear training case:

- the stance output itself is `SUPPORT`
- the failure happens because the surviving evidence is not strong enough to force a verdict
- that looks more like evidence strength / threshold / passage quality than stance classification

Primary classification:

- `passage_strength_or_threshold_issue`

Secondary classification:

- `retrieval_or_relevance_issue`

Phase 5 decision:

- do not treat this as a pure stance-training seed yet

## Summary Table

- `5G networks spread coronavirus` -> `runtime_logic_issue`
- `The Great Wall of China is visible from space` -> `ambiguity_or_definition_issue`
- `The Amazon River is the longest river in the world` -> `ambiguity_or_definition_issue`
- `Humans share about 50 percent of their DNA with bananas` -> `passage_strength_or_threshold_issue`

Count of likely pure stance failures:

- `0` clear cases

Count of mixed/unclean cases:

- `4`

## Phase 5 Gate Decision

Current decision:

- Phase 5 should **not** proceed to stance retraining yet

Reason:

- the current residual set does not provide a clean pool of genuine stance-model failures
- training stance on these failures would likely bake in retrieval, ambiguity, and runtime-logic noise

## What Phase 5 Can Legitimately Do Now

Allowed next actions:

1. Keep this taxonomy as the written gate for future stance work.
2. Collect additional residual failures from future live runs.
3. Add only clearly isolated stance failures to a future `stance v6` or equivalent seed set.
4. Revisit stance retraining only when there are enough clean stance failures to justify it.

Not recommended now:

1. Training a new stance checkpoint from the current 4 residual misses.
2. Claiming Phase 5 is a model-training phase already in progress.

## Current Best Interpretation

The project is ready for Phase 5 analysis, but not yet for Phase 5 stance retraining.

That means:

- Phase 5 has started only as residual taxonomy and gating
- Phase 5 model training remains deferred
