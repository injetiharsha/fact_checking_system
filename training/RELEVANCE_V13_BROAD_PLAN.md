# Relevance v13 Broad Plan

`v9_run1` remains the best current runtime checkpoint. The goal of `v13` is not to replace it quickly, but to build a dataset large enough to justify a real refresh.

## Why v12 was not enough

- too small
- too residual-only
- too narrow in domain coverage
- not enough diverse negatives

## v13 target size

- minimum useful addition: `500-1,000` new records
- better target: `2,000+` records

## Dataset mix

- `40%` broad factual relevance examples
- `20%` authoritative-source vs derivative-source examples
- `15%` myth/debunking and contradiction-bearing cases
- `15%` India civic/government/entity/acronym cases
- `10%` comparisons, numeric/date, and edge-structure claims

## Inputs to combine

### Existing repo datasets

- `data/relevance/v9`
- `data/relevance/v12_source_residual`
- older manual and residual builders under `training/common/build_relevance_v*.py`

### Public/local raw data

- `data/public/averitec/train.json`
- `data/public/averitec/dev.json`

### New local curation

- benchmark residuals where a good page existed but a weaker page or sentence won
- India-focused official-source claims
- acronym/entity claims like `ISRO`, `ECI`, ministries, commissions, schemes

## Record shape

Keep the existing relevance format:

- `claim`
- `candidate_sentence`
- `label`
- `source`
- `source_url`
- `selection_origin`

## Public-data usage

Use public datasets to add broad claim/evidence variety, but do not depend on them alone.

Recommended role:

- `AVeriTeC`: broad factual claim/evidence pairs and hard negatives
- current repo seeds: residual structure and claim families already known to matter
- local curation: India and source-quality failures the public sets will miss

## Success criteria before training

- at least `500+` new records beyond the current v9/v12 blend
- balanced positives and negatives
- at least `100+` India/government/entity-style records
- at least `100+` authoritative-vs-derivative source examples
- no heavy dependence on one dataset family

## Runtime policy

Until a broader `v13` proves itself:

- keep `RELEVANCE_CHECKPOINT=checkpoints/relevance/v9_run1`
- treat `v12_source_residual_run1` as experimental only
