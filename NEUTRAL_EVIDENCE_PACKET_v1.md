# Neutral Evidence Packet v1

This packet isolates the current `neutral_despite_evidence` / evidence-survival failures without mixing in:

- claim-checkability blocks
- broad support-bias false positives
- invalid search-collapsed runs

## Purpose

Use this packet to inspect why obviously checkable claims are still ending as `NEUTRAL` or weakly scored despite retrieval producing relevant source material.

The likely failure modes are:

- direct-answer passages not surviving selection
- strong passages surviving but staying too weak for decisive promotion
- document consolidation retaining weaker neutral passages over clearer answer passages
- source choice landing on derivative or shell-like pages instead of decisive primary/explainer pages

## Claims Included

- `Lake Baikal is the deepest lake on Earth` -> `TRUE`
- `DNA is shaped like a double helix` -> `TRUE`
- `Jupiter is the largest planet in the solar system` -> `TRUE`
- `Humans can breathe in space without equipment.` -> `FALSE`
- `The Pacific Ocean is the largest ocean on Earth.` -> `TRUE`
- `Chennai is the capital of Karnataka.` -> `FALSE`
- `The Titanic completed its first voyage successfully.` -> `FALSE`
- `The decimal system uses base ten rather than base twelve.` -> `TRUE`
- `The Indian Space Research Organisation is commonly known by the acronym ISRO.` -> `TRUE`
- `The Election Commission of India is a private company.` -> `FALSE`
- `Penguins can fly long distances over the ocean.` -> `FALSE`

## Run

```powershell
.\.venv\Scripts\python.exe benchmark_multi_test.py --claims-file benchmark_claims\neutral_evidence_packet_v1.json --output logs\neutral_evidence_packet_v1_results.json
```

## What To Inspect

- `failed_by_category`
- per-claim `transparency.evidence_stats`
- document-level retained passages
- whether selected evidence is direct, complete, and source-reliable
- whether decisive passages are present in raw retrieval but lost later

## Success Criteria

- fewer `NEUTRAL` outputs on these claims
- no new rise in support-side false positives
- no need for broad heuristic scoring changes
