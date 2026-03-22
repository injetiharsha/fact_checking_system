# Phase 2 Narrow Follow-Up

Status: monitoring-driven follow-up as of 2026-03-22

This note defines the current narrow Phase 2 scope after the first full monitoring cycle on the recommended stack.

Phase 2 is **not** broadly reopened.
Phase 2 is on **reopen_watch** because recurring valid residuals now include a small relevance-ranked set.

## Source of Truth

Primary monitoring artifacts:

- `logs/monitoring_cycles/monitoring_live_2026-03-22/baseline_30claim.json`
- `logs/monitoring_cycles/monitoring_live_2026-03-22/multilingual_regression.json`
- `logs/monitoring_cycles/monitoring_live_2026-03-22/fresh_realtime.json`
- `logs/residual_ledger.json`

## Current Phase 2 Watchlist

Recurring `relevance_ranking` residuals now include:

- `Humans share about 50 percent of their DNA with bananas`
- `Neptune is the farthest planet from the Sun`
- Telugu AP farmer alert claim
- Telugu `Mars has two moons`
- `CDC said the MMR vaccine causes measles outbreaks.`
- `NOAA reported another large marine heatwave in West Coast waters in March 2026.`
- `NOAA said the current West Coast marine heatwave is an El Nino event.`

## Residual Split

### A. Plausible True Phase 2 Candidates

These are the best candidates for a narrow relevance-side revisit:

- `Humans share about 50 percent of their DNA with bananas`
  - recurring `NEUTRAL`
  - prior spot-check showed weak or meta-shell evidence surviving instead of substantive explainer evidence

- `CDC said the MMR vaccine causes measles outbreaks.`
  - recurring `NEUTRAL`
  - likely needs stronger contradiction-bearing sentence selection from authoritative health sources

- `NOAA reported another large marine heatwave in West Coast waters in March 2026.`
  - recurring `NEUTRAL`
  - likely needs better survival of direct-answer official sentences

- `NOAA said the current West Coast marine heatwave is an El Nino event.`
  - recurring `NEUTRAL`
  - likely needs better contradictory sentence survival from NOAA source text

### B. Retrieval / Source-Quality Issues Masquerading as Phase 2

These should not be treated as clean relevance-model failures yet:

- `Neptune is the farthest planet from the Sun`
  - latest monitoring run still collapsed too early at retrieval/source level
  - prior manual inspection showed search-preview / source-shell behavior

- Telugu AP farmer alert claim
  - multilingual local-admin/payment claim
  - still looks entangled with local-source interpretation and multilingual evidence handling

- Telugu `Mars has two moons`
  - multilingual true-control claim
  - likely still mixed between multilingual retrieval/routing and evidence survival

## Current Decision

Phase 2 should stay narrow and non-heuristic.

Do **not**:

- reopen broad relevance retraining
- add claim-shaped rules
- change the whole retrieval stack

Do:

- focus only on the four English recurring `neutral_despite_evidence` cases first
- treat the multilingual pair and `Neptune` as adjacent retrieval/source issues unless repeated evidence proves otherwise

## Next Acceptable Phase 2 Work

Only three kinds of follow-up are in scope:

1. Better evidence selection from already-retrieved authoritative pages
   - especially direct-answer and contradiction-bearing sentences
   - without claim-specific rules

2. Cleaner exclusion of shell/meta/search-preview text through general source-quality logic
   - only if it is general-purpose and not tuned to a single claim

3. Relevance-evaluation expansion
   - add a small Phase 2 residual packet built from the four English recurring neutral cases
   - use that packet to decide whether a model-side relevance follow-up is justified

## Phase Gate

Reopen Phase 2 more seriously only if a second monitoring cycle still shows a recurring relevance-ranked set centered on:

- `bananas`
- `CDC/MMR`
- `NOAA marine heatwave`
- `NOAA El Nino`

If those persist, the next step is a **small general relevance-side improvement or residual evaluation packet**, not a broad retraining pass.
