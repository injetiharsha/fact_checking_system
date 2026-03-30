# Real Bottlenecks Plan

## Goal

Pause broad model churn and focus only on the three bottlenecks that are still limiting runtime quality:

- evidence retrieval quality
- source selection
- multilingual checkability over-blocking

This plan is intentionally narrow. It avoids new heuristic patches unless a temporary safety guard is absolutely necessary.

## Current Stable Runtime

Keep this as the default working stack while improvement work is in progress:

- `STANCE_CHECKPOINT=checkpoints/stance/stage2_hardcases_v3_bias`
- `RELEVANCE_CHECKPOINT=checkpoints/relevance/v9_run1`
- `CLAIM_CHECKABILITY_CHECKPOINT=checkpoints/claim_checkability/v2_run2`
- `ENABLE_RETRIEVAL_V2=0`
- `ENABLE_VERIFIER_V2=0`
- `ENABLE_LLM_VERIFIER=1`
- `LLM_VERIFIER_POLICY=neutral_only`

Do not switch runtime to experimental relevance checkpoints until they beat this stack on real benchmarks.

## Phase 0: Freeze And Measure

Purpose:
- stop checkpoint churn
- keep a stable comparison point
- collect clean residual evidence before changing anything

Tasks:
- keep the stable runtime stack unchanged
- rerun only the existing benchmark slices when needed:
  - 30-claim baseline
  - 68-claim mixed benchmark
  - multilingual stage-2 benchmark
  - support-bias packet
  - neutral-evidence packet
- treat invalid or search-collapsed runs as non-decision artifacts
- keep residual notes focused on recurring failures only

Exit condition:
- a stable baseline exists for all future comparisons

## Phase 1: Retrieval Quality Audit

Purpose:
- separate true retrieval failure from later ranking/selection failure

Questions to answer:
- was the right source retrieved at all?
- was the right source retrieved but buried?
- was the right source retrieved and scored, but lost later?

Priority failure types:
- `neutral_despite_evidence`
- multilingual claims that should be easy factual wins
- English claims like:
  - `DNA is shaped like a double helix`
  - `Jupiter is the largest planet in the solar system`
  - `Neptune is the farthest planet from the Sun`
  - `The Indian Space Research Organisation is commonly known by the acronym ISRO`

Tasks:
- capture retrieval traces for recurring misses
- label each miss as one of:
  - `source_not_found`
  - `source_found_but_weakly_ranked`
  - `good_source_found_but_bad_passage_survived`
  - `search_noise_or_derivative_source_win`
- build a retrieval audit table for 30 to 50 residual claims before any new training round

Output:
- one retrieval audit sheet or JSON artifact with claim-level diagnosis

Exit condition:
- at least 80 percent of recurring misses are classified into a concrete retrieval-stage failure bucket

## Phase 2: Source Selection Improvement

Purpose:
- improve which source and which passage survives after retrieval
- do this with data, not scoring hacks

Scope:
- authoritative-source wins
- direct-answer sentence wins
- derivative/news-shell sentence loses
- contradiction-bearing sentence wins for false claims

Tasks:
- expand the existing source-selection residual data
- grow beyond tiny residual sets into a broader curated layer
- target claim families such as:
  - science facts
  - geography and capitals
  - India civic and official bodies
  - acronym/entity claims
  - myth/debunking claims
  - numeric/date claims
  - comparison claims
- for each claim, store:
  - claim text
  - positive decisive sentence
  - one or more topical-but-weaker negatives
  - source URL and source type

Dataset rule:
- no duplicate claim/candidate/label rows after normalization
- prefer source diversity over paraphrase spam

Training rule:
- do not train a new relevance checkpoint until the broadened residual layer is materially larger and more balanced than the recent `v12` and `v13` experiments

Exit condition:
- a broadened source-selection dataset exists and passes a manual spot-check for source diversity and label quality

## Phase 3: Multilingual Checkability Repair

Purpose:
- stop valid multilingual factual claims from being blocked before search

Current known issue:
- some multilingual live or official claims are being marked `not_checkable_other` when they are clearly fact-checkable

Tasks:
- collect multilingual blocked examples from runtime traces
- separate them into:
  - true non-checkable inputs
  - valid factual claims wrongly blocked
- build a multilingual checkability residual packet with native-script claims across:
  - Hindi
  - Telugu
  - Tamil
  - Kannada
  - Malayalam
- add more positive factual examples for:
  - government announcements
  - civic/institutional statements
  - geography facts
  - short encyclopedic claims
- retrain only after the multilingual factual-positive side is materially larger

Important rule:
- do not weaken the gate with loose heuristics just to force multilingual claims through
- improve recall using training data, not regex exceptions

Exit condition:
- blocked multilingual factual claims drop materially on the multilingual benchmark without a large rise in junk acceptance

## Phase 4: Evaluation Gates

Purpose:
- prevent another cycle of strong training metrics with weak pipeline outcomes

Any candidate change must be evaluated on:
- 30-claim baseline
- 68-claim mixed benchmark
- multilingual stage-2 benchmark
- support-bias packet
- neutral-evidence packet when relevant

Promotion rules:
- do not promote if it improves training metrics but worsens general benchmark accuracy
- do not promote if it improves multilingual results but harms the stable English-heavy benchmarks too much
- do not promote if false-positive safety degrades materially

Practical decision order:
1. retrieval/source improvement must not break support-bias gains
2. multilingual checkability must not over-open junk inputs
3. experimental relevance models must beat `v9_run1` on real benchmarks, not only on validation loss

## Immediate Next Work When Resuming

Start here next time:
1. run a retrieval audit on the recurring `neutral_despite_evidence` set
2. build a clean claim-level retrieval/source diagnosis sheet
3. collect multilingual factual claims that were wrongly blocked by checkability
4. only after that, decide whether the next training effort is:
   - source-selection relevance data expansion
   - multilingual checkability retraining
   - or both in separate tracks

## Non-Goals For Now

Do not spend time on these until the bottlenecks above are addressed:
- more broad relevance checkpoint experimentation
- more tiny residual-only model runs
- blanket sentence-length or scoring heuristics
- raw-performer stack promotion
- reopening paused pipeline phases without recurring benchmark evidence

## Bottom Line

The system is already in a usable state on the stable stack.
The next improvement cycle should be:

- stabilize
- diagnose
- improve with targeted data
- benchmark before promotion
