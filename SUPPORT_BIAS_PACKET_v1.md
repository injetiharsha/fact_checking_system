# Support Bias Packet v1

Status: created after the clean 68-claim recommended-stack run with `claim_checkability v2_run2`

This packet isolates the remaining support-side false positives from:

- `logs/claim_seed_100_mixed_v1_benchmark_results_v2_run2.json`

## Purpose

Use this packet to test the next follow-up stage cleanly.
The main goal is to reduce `false_positive_support_bias` without mixing in:

- checkability blocks
- multilingual encoding issues
- live-claim variability
- general neutral/insufficient-evidence noise

## Current Packet Claims

All 8 rows are expected `FALSE`:

- `Venus is the closest planet to the Sun.`
- `The Moon is a planet.`
- `Bananas are vegetables.`
- `Chennai is the capital of Karnataka.`
- `Bats are blind.`
- `The moon landing was faked.`
- `The Indus Valley Civilization was located in Antarctica.`
- `The Amazon River is longer than the Nile River.`

## Why These Matter

They represent the current dominant quality failure after the claim-checkability retrain improved blocked-claim recall.

The shared pattern is not missing search coverage.
The shared pattern is that topically related evidence is being over-promoted as support instead of decisive contradiction winning.

## Main Semantic Subtypes Inside This Packet

- taxonomy/class-membership errors
  - `The Moon is a planet.`
  - `Bananas are vegetables.`

- geography/location mismatch
  - `Chennai is the capital of Karnataka.`
  - `The Indus Valley Civilization was located in Antarctica.`

- common myth-style falsehoods
  - `Bats are blind.`
  - `The moon landing was faked.`

- comparison / nearest-longest relation mistakes
  - `Venus is the closest planet to the Sun.`
  - `The Amazon River is longer than the Nile River.`

## Acceptable Follow-Up

Keep the follow-up narrow and non-heuristic.

In scope:

1. Better contradiction-bearing sentence survival from already retrieved authoritative pages
2. General support-bias suppression when evidence is only topically similar but relation-mismatched
3. Ranking changes that prefer explicit contradiction over weak descriptive overlap

Out of scope:

- broad stack switching
- claim-specific rules
- special cases for individual claims
- reopening unrelated phases

## Run Command

```powershell
.\.venv\Scripts\python.exe benchmark_multi_test.py --claims-file benchmark_claims\support_bias_packet_v1.json --output logs\support_bias_packet_v1_results.json
```

## Success Criteria

Good progress would look like:

- fewer `TRUE` predictions on this packet
- more `FALSE` or at least safer `NEUTRAL`
- no new checkability blocking on these factual rows
