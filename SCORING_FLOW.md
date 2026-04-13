# Scoring Flow

This document explains how scoring works from `Run Analysis` to the final verdict in the current claim-analysis pipeline.

## Entry Path

1. API entry:
   - [routes.py](/f:/fact_checking_system/routes.py#L150)
   - `POST /check`
2. Main pipeline:
   - [pipeline/claim_pipeline.py](/f:/fact_checking_system/pipeline/claim_pipeline.py#L985)
   - `ClaimPipeline.run(...)`

## High-Level Flow

1. Claim enters `ClaimPipeline.run(...)`
2. Claim type, context, and checkability are computed
3. Evidence is retrieved through the router
4. Best sentences are extracted from raw evidence documents
5. Each candidate sentence gets:
   - relevance score
   - quality score
   - effective relevance
6. Evidence is filtered into `strong`, `soft`, or rejected
7. Shortlisted evidence gets stance:
   - direct stance model
   - or `VerifierV2`
   - optional LLM verifier override
8. Weighted support/refute scores are computed
9. Initial verdict is produced
10. Final guardrails may still convert it to `NEUTRAL`

## Detailed Score Table

| Stage | Score / Signal | Formula / Rule | Default / Threshold | Used For | File |
|---|---|---|---|---|---|
| Sentence selection | `selector_score` | Produced inside `extract_best_sentences(...)` from sentence-selection heuristics and fast matching | internal | Helps choose best snippet from page text | [pipeline/claim_pipeline.py:189](/f:/fact_checking_system/pipeline/claim_pipeline.py#L189) |
| Relevance | `relevance_score` | `self.relevance_scorer.score(claim, sentence)` | model-dependent | Claim-evidence semantic match | [pipeline/claim_pipeline.py:1365](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1365), [evidence/relevance.py:306](/f:/fact_checking_system/evidence/relevance.py#L306) |
| Quality | `quality_score` | Heuristic text score based on length, numbers, punctuation, factual phrasing, penalties for metadata/reporting | `0..1` | Filters weak/junky evidence | [pipeline/claim_pipeline.py:1368](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1368), [evidence/quality.py:10](/f:/fact_checking_system/evidence/quality.py#L10) |
| Effective relevance | `effective_relevance` | `min(1.0, relevance*0.85 + selector*0.15)` | computed | Final relevance used for evidence acceptance | [pipeline/claim_pipeline.py:1370](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1370) |
| Strong evidence gate | `strong_relevance_threshold` | `effective_relevance >= threshold` | `0.45` | Marks evidence as `strong` | [pipeline/claim_pipeline.py:393](/f:/fact_checking_system/pipeline/claim_pipeline.py#L393), [pipeline/claim_pipeline.py:1380](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1380) |
| Strong evidence gate | `strong_quality_threshold` | `quality_score >= threshold` | `0.4` | Marks evidence as `strong` | [pipeline/claim_pipeline.py:394](/f:/fact_checking_system/pipeline/claim_pipeline.py#L394), [pipeline/claim_pipeline.py:1380](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1380) |
| Soft evidence gate | `soft_relevance` / `soft_quality` | Pulled from `scoring_profile` | profile-based | Allows `soft` evidence instead of reject | [pipeline/claim_pipeline.py:1386](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1386) |
| Evidence combined score | `combined_score` | `effective_relevance * quality_score` | computed | Stored for later weighted scoring | [pipeline/claim_pipeline.py:1412](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1412) |
| Evidence weight | `weight` | Source credibility weight from router; softened for non-top soft evidence | source-dependent | Major part of final strength | [pipeline/claim_pipeline.py:1378](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1378), [pipeline/claim_pipeline.py:1391](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1391) |
| Stance raw confidence | `confidence` | Returned by stance model / verifier | model-dependent | Used in final evidence strength and guardrails | [pipeline/claim_pipeline.py:1632](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1632), [semantic/stance_model.py:39](/f:/fact_checking_system/semantic/stance_model.py#L39) |
| Stance label normalization | `label -> stance` | `LABEL_0->REFUTE`, `LABEL_1->NEUTRAL`, `LABEL_2->SUPPORT`, `SUPPORTS->SUPPORT`, `REFUTES->REFUTE` | exact mapping | Normalizes model output | [semantic/stance_model.py:42](/f:/fact_checking_system/semantic/stance_model.py#L42) |
| Stance postfilter | `_postfilter_model_stance` | Rejects weak support/refute, returns `None` -> later neutral | threshold-heavy | Major neutral source | [semantic/stance_model.py:382](/f:/fact_checking_system/semantic/stance_model.py#L382) |
| LLM verifier override | `llm_result` | Can replace evidence stance if allowed | env-gated | Late evidence-level re-stance | [pipeline/claim_pipeline.py:1567](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1567) |
| Year rescue | heuristic | If neutral and year logic matches, set support/refute | `0.88` confidence | Neutral rescue | [pipeline/claim_pipeline.py:1592](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1592) |
| Rank rescue | heuristic | If neutral and numeric rank logic matches | `0.9/0.86` confidence | Neutral rescue | [pipeline/claim_pipeline.py:1600](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1600) |
| Numeric proximity rescue | heuristic | If numbers differ by <= 2% in allowed factual domains -> support | `0.82` confidence | Approximate numeric claims | [pipeline/claim_pipeline.py:1608](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1608) |

## Quality Score Breakdown

Source:
- [evidence/quality.py:10](/f:/fact_checking_system/evidence/quality.py#L10)

| Rule | Effect |
|---|---|
| length >= 12 words | `+0.25` |
| length > 30 | `+0.40` |
| length > 80 | `+0.10` |
| contains a digit | `+0.20` |
| contains `.` | `+0.15` |
| contains factual verbs like `is/are/was/has/cannot/does not` | `+0.20` |
| contains reporting markers like `according to`, `reportedly`, `min read` | `-0.15` |
| contains metadata markers like `image credit`, `copyright`, `publication date` | `-0.35` |
| ends with `?` | `-0.15` |
| final cap | `min(score, 1.0)` |

## Relevance Score Path

Source:
- [evidence/relevance.py:306](/f:/fact_checking_system/evidence/relevance.py#L306)

Order used by `RelevanceScorer.score(...)`:

1. score cache
2. BGE reranker if loaded
3. trained relevance subprocess checkpoint if configured
4. cross-encoder if loaded
5. semantic encoder score
6. lexical fast fallback

So `relevance_score` is backend-dependent. It is not one fixed formula.

## Evidence Acceptance

Source:
- [pipeline/claim_pipeline.py:1380](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1380)

| Condition | Outcome |
|---|---|
| `effective_relevance >= strong_relevance` and `quality >= strong_quality` | `evidence_tier = strong` |
| else if `effective_relevance >= soft_relevance` and `quality >= soft_quality` | `evidence_tier = soft` |
| else | reject evidence |

If no evidence survives:
- final verdict immediately becomes `NEUTRAL`
- [pipeline/claim_pipeline.py:1459](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1459)

## Weighted Evidence Strength

Source:
- [verdict/weighted_score.py:9](/f:/fact_checking_system/verdict/weighted_score.py#L9)

For each non-neutral evidence item:

1. `base_strength = weight * confidence`
2. `quality_signal = combined_score`
   - if missing: `relevance_score * quality_score`
3. `blended_strength = 0.8 * base_strength + 0.2 * quality_signal`

Bonuses:

- if `evidence_tier == "strong"` -> `+0.03`
- if repeated same-direction passages > 1 -> `+ min(0.08, 0.03 * (n-1))`

Final:

- `final_strength = min(1.0, blended_strength)`

Evidence is ignored if:

- stance is `NEUTRAL`
- or `final_strength < 0.2`

Then:

- support evidence sums into `support_score`
- refute evidence sums into `refute_score`

## First Verdict Engine

Source:
- [verdict/final_report.py:16](/f:/fact_checking_system/verdict/final_report.py#L16)

Thresholds:

- `min_total_score_for_definitive_verdict = 0.35`
- `min_score_gap_for_definitive_verdict = 0.15`

Rules:

| Rule | Result |
|---|---|
| `support_score == 0` and `refute_score == 0` | `NEUTRAL` |
| `support_score + refute_score < 0.35` | `NEUTRAL` |
| `abs(support_score - refute_score) < 0.15` | `NEUTRAL` |
| `support_score > refute_score` | `TRUE` |
| `refute_score > support_score` | `FALSE` |
| otherwise | `NEUTRAL` |

## Confidence Calculation

Source:
- [verdict/confidence.py:11](/f:/fact_checking_system/verdict/confidence.py#L11)

Formula:

1. `raw = abs(support_score - refute_score) / (support_score + refute_score)`
2. if score gap below threshold, multiply by `0.75`
3. apply domain-diversity penalty if evidence is concentrated on too few domains
4. if final verdict is neutral later, cap with `min(confidence, 0.55)`

## Final Guardrails In Claim Pipeline

These run after the first verdict and can still force `TRUE` or `FALSE` back to `NEUTRAL`.

Sources:
- [pipeline/claim_pipeline.py:1715](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1715)
- [pipeline/claim_pipeline.py:1813](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1813)
- [pipeline/claim_pipeline.py:1832](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1832)

Current defaults:

- `single_source_decisive_confidence = 0.8`
- `single_source_min_weight = 0.65`

| Guardrail | Threshold / Rule | Effect |
|---|---|---|
| decisive single-source | any support/refute item with `confidence >= 0.8` and `weight >= 0.65` | can preserve definitive verdict |
| no strong evidence and no decisive single and no soft consensus | force neutral | major neutral source |
| `non_neutral_count == 0` | force neutral | major neutral source |
| all evidence neutral and retry allowed | rerun with expanded search cap | retry path |
| `TRUE` but no external support item with confidence >= `0.58` | force neutral |
| `FALSE` but no external refute item with confidence >= `0.58` | force neutral |
| mixed support/refute and low margin | if final confidence < `0.4` or strength margin < `0.2`, force neutral |

## Where Neutrals Mostly Come From

Two main places:

1. stance postfilter:
   - [semantic/stance_model.py:382](/f:/fact_checking_system/semantic/stance_model.py#L382)
2. final verdict guardrails:
   - [pipeline/claim_pipeline.py:1715](/f:/fact_checking_system/pipeline/claim_pipeline.py#L1715)

So many `NEUTRAL` outcomes are not from label mismatch. They usually come from:

- stance refusing to commit
- final verdict engine deciding evidence is not decisive enough

## Practical Summary

The scoring chain is:

1. retrieve documents
2. extract best sentences
3. compute `relevance_score`
4. compute `quality_score`
5. compute `effective_relevance`
6. keep only strong/soft evidence
7. get evidence stance and stance confidence
8. compute evidence final strength
9. sum support and refute strengths
10. produce initial verdict
11. apply final abstention guardrails

The biggest knobs that currently control final verdict behavior are:

- `effective_relevance`
- `quality_score`
- stance `confidence`
- evidence `weight`
- `support_score`
- `refute_score`
- `single_source_decisive_confidence`

