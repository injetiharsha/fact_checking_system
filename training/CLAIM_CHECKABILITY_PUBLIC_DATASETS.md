# Claim Checkability Public Datasets

Status: source guide as of 2026-03-23

This note lists the public dataset types that are most useful for the
claim-checkability gate.

It is narrower than the general project dataset notes because this task is not
stance verification. It is a pre-retrieval checkability decision.

## Best Fits

### 1. ClaimBuster

Use for:

- check-worthiness style supervision
- separating factual/check-worthy statements from weaker non-check-worthy text

Best contribution:

- `factual_claim`
- some `other_uncheckable`

Important caution:

- do not assume all non-check-worthy rows are personal statements or opinions
- use only clear mappings

### 2. CheckThat! Task 1

Use for:

- check-worthiness in social and multigenre text
- multilingual or code-mixed examples when available

Best contribution:

- `factual_claim`
- `question_or_rewrite`
- `other_uncheckable`

Important caution:

- label semantics differ by year and subtask
- record exactly which edition and split were used

## Partial Fits

### 3. FEVER

Use for:

- short factual claim positives only

Not good for:

- `personal_statement`
- `opinion`
- `other_uncheckable`

### 4. AVeriTeC

Use for:

- real fact-check style `factual_claim` positives

Not good for:

- general uncheckable boundary learning

### 5. SciFact

Use for:

- scientific factual claims

Not good for:

- broad social-media-like non-checkable text

## What Public Data Will Not Cover Well

These classes still need strong local curation:

- `personal_statement`
- `opinion`
- India-specific social phrasing
- short fragment/junk text
- local-language noisy inputs

## Recommended Use Strategy

1. Public datasets for `factual_claim` backbone
2. Local curated data for the uncheckable side
3. Multilingual India-focused examples added manually or via local collection
4. Keep provenance notes for every external source used
