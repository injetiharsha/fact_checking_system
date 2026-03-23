# Claim Checkability Data Plan

Status: proposed data plan as of 2026-03-23

This note defines how to build a practical training dataset for the
claim-checkability gate.

The runtime gate only needs one final decision:

- `checkable`
- `uncheckable`

But the training set should keep richer internal labels so the model learns
cleaner boundaries:

- `factual_claim`
- `personal_statement`
- `opinion`
- `question_or_rewrite`
- `other_uncheckable`

At runtime:

- `factual_claim` -> `checkable`
- every other label -> `uncheckable`

## Why We Need More Than `v1`

Current seed dataset:

- location: `data/claim_checkability/v1`
- total rows: `50`
- source: local seed examples only

That is enough for a prototype smoke-training run, but not enough for a stable
deployment gate.

Main weaknesses of `v1`:

- too small
- too clean and synthetic
- weak multilingual coverage
- weak India-specific viral/social wording coverage
- not enough near-boundary examples

## Recommended Dataset Shape

Target a `v2` dataset with at least:

- `800` to `1,500` total rows for a first useful trained gate

Suggested class balance:

- `factual_claim`: `250` to `400`
- `personal_statement`: `120` to `250`
- `opinion`: `120` to `250`
- `question_or_rewrite`: `120` to `250`
- `other_uncheckable`: `120` to `250`

This does not need to be perfectly balanced, but no class should be tiny.

## Data Sources

Use a mixed strategy:

1. Public datasets for the checkable/check-worthy backbone
2. Local curated examples for the non-checkable classes
3. India-focused and multilingual local examples for deployment realism

### A. Public Backbone

Best public sources for this task:

1. ClaimBuster
- best fit for check-worthiness style supervision
- use it to expand `factual_claim` and some `other_uncheckable`
- map only clear cases; avoid noisy borderline rows

2. CheckThat! Task 1
- useful for check-worthiness in tweets, speeches, and multigenre text
- especially helpful if multilingual or code-mixed data is available
- use it to expand:
  - `factual_claim`
  - `question_or_rewrite`
  - `other_uncheckable`

3. FEVER / AVeriTeC / SciFact
- use only to expand `factual_claim`
- these are not checkability datasets, but they are good sources of short,
  clean factual claims

### B. Local Curated Data

These classes should mostly come from local curation:

- `personal_statement`
- `opinion`
- `other_uncheckable`

Examples to include:

- personal captions
- self-descriptions
- vague reactions
- meme-like fragments
- `read this`, `must watch`, `so true`
- emotional or judgmental statements

### C. India-Focused Coverage

Because the product is India-focused, include:

- English
- Hinglish
- Telugu
- Hindi
- Tamil
- Kannada

And include realistic categories such as:

- government scheme alerts
- election/policy claims
- local administrative notices
- weather/disaster warnings
- public-health claims
- social-post fragments and caption text

## Labeling Policy

Use these rules:

### `factual_claim`

Text makes a concrete statement that could be verified or falsified with
evidence.

Examples:

- `The moon landing was faked.`
- `Mars has two moons.`
- `ISRO launched Chandrayaan-3 in 2023.`

### `personal_statement`

Text is mainly about the speaker, their identity, feelings, possessions, or
personal condition.

Examples:

- `This is me.`
- `I am from Hyderabad.`
- `My name is Rahul.`

### `opinion`

Text expresses taste, judgment, preference, or evaluation rather than a clearly
verifiable claim.

Examples:

- `This movie is amazing.`
- `That policy is terrible.`
- `This restaurant is overrated.`

### `question_or_rewrite`

Text is a question or request that should be rewritten into a declarative claim
before fact-checking.

Examples:

- `Did NASA fake the moon landing?`
- `What happened in Berlin?`
- `Is this true?`

### `other_uncheckable`

Text is not a meaningful fact-check target but does not clearly fit the other
uncheckable classes.

Examples:

- `wow`
- `must watch`
- `viral video`
- `read this`

## Suggested Collection Order

1. Keep the current `v1` seed set as the base
2. Add `200` to `300` curated local examples first
3. Add public factual/check-worthy rows
4. Add India-focused and multilingual examples
5. Rebalance classes
6. Build `data/claim_checkability/v2`

## Near-Boundary Examples To Include

These are especially important because they teach the model where not to
over-block:

- short but valid claims
  - `Mars has two moons.`
  - `The Sun is a star.`
- short but uncheckable text
  - `this is me`
  - `must watch`
- opinion-like but partly factual text
  - `This phone has a great camera.`
- rhetorical question forms
  - `Could 5G spread coronavirus?`
- local-admin viral phrasing
  - short warning-style claims that still contain checkable content

## Colab Recommendation

Colab is optional for `v1`.
Colab becomes more useful for `v2` once:

- the dataset grows beyond a few hundred rows
- we want repeatable training and checkpoint archiving
- we want to test a slightly larger encoder without local resource friction

Recommended practical order:

1. build `v2`
2. run one local smoke training
3. if the dataset is large enough and the smoke run looks promising, move the
   full run to Colab

## Deliverables For The Next Step

Before the first serious training run, we should add:

- a `v2` dataset builder
- one local curated seed file for manual examples
- one mapping note for any public datasets we ingest
- one provenance entry per external dataset source

## Decision Rule

We should only switch runtime from heuristic fallback to trained gate if the
trained model is clearly better on:

- short factual claims
- personal statements
- opinions
- questions
- India-focused noisy/social phrasing

If it only matches the heuristics on clean toy data, it should not replace the
fallback yet.
