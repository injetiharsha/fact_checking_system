# Public Mapping Notes

Status: initial placeholder as of 2026-03-23

Use this note to record how public dataset labels are mapped into the
claim-checkability training labels.

Current target labels:

- `factual_claim`
- `personal_statement`
- `opinion`
- `question_or_rewrite`
- `other_uncheckable`

## Planned Public Sources

### ClaimBuster

Intended use:

- map clear factual/check-worthy statements into `factual_claim`
- map only clearly weak non-check-worthy text into `other_uncheckable`

Do not:

- force all non-check-worthy rows into one fine-grained class without review

### CheckThat! Task 1

Intended use:

- map clearly check-worthy text into `factual_claim`
- map question-style or rewrite-needed text into `question_or_rewrite` when the
  source format makes that distinction trustworthy
- map weak non-check-worthy snippets into `other_uncheckable`

### FEVER / AVeriTeC / SciFact

Intended use:

- use only as `factual_claim` positives

Do not:

- use them to create uncheckable classes

## Next Update

When a real public dataset is added:

1. record the exact source and split in [DATA_PROVENANCE.md](/f:/fact_checking_system/training/DATA_PROVENANCE.md)
2. replace placeholder rows in `data/claim_checkability/seeds/public_mapped_v2.jsonl`
3. note the exact label mapping here
