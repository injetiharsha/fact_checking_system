# Project Status Detailed

## Overall State

The project is in a much stronger state than before, but it is not finished in the sense of having fully reliable fact-check quality across claim types, source types, and languages. The system now has a real claim-checkability gate, a stronger stance checkpoint, cleaner frontend behavior, and a much better benchmark workflow. The biggest remaining limitation is still downstream: retrieval quality, source selection, and decisive evidence survival.

At a high level, the system is now good enough to operate as a serious prototype and iterate safely, but not yet good enough to claim best-in-class reliability.

## Current Stable Runtime Stack

This is the best known practical stack right now and should be treated as the runtime baseline unless a future checkpoint clearly beats it in benchmarks:

- Relevance checkpoint: `checkpoints/relevance/v9_run1`
- Stance checkpoint: `checkpoints/stance/stage2_hardcases_v3_bias`
- Claim-checkability checkpoint: `checkpoints/claim_checkability/v2_run2`
- `ENABLE_RETRIEVAL_V2=0`
- `ENABLE_VERIFIER_V2=0`
- `ENABLE_LLM_VERIFIER=1`
- `LLM_VERIFIER_POLICY=neutral_only`

This stack was selected because it gives the best quality/safety/runtime balance among the variants tested so far.

## What Has Been Finished

### 1. Claim-checkability gate

This is one of the biggest completed improvements.

Before this work:
- any non-empty sentence could go into the fact-check pipeline
- personal statements, vague text, and non-checkable inputs were often analyzed as if they were factual claims

What was completed:
- created a dedicated claim-checkability module instead of burying the logic in the pipeline
- designed a trainable label structure with a binary runtime gate
- built and expanded a claim-checkability dataset
- trained multiple checkpoints
- promoted `v2_run2` as the best current checkpoint
- integrated the trained gate before retrieval
- benchmarked heuristic vs trained gate

Current outcome:
- runtime behavior is much better on junk, opinion, personal, and non-checkable inputs
- the gate no longer depends only on heuristics
- overblocking on short factual claims was reduced substantially compared with the earlier version

Current status:
- finished enough for runtime use
- still needs multilingual robustness improvements

### 2. Stance / support-bias improvement

This was the second major completed system improvement.

Problem before:
- topic-near evidence was often promoted as support
- some false claims received dangerous wrong `TRUE` verdicts

Examples included:
- `The Moon is a planet`
- `The moon landing was faked`
- `The Amazon River is longer than the Nile River`

What was completed:
- built a focused support-bias benchmark packet
- ran narrow stance diagnostics
- rejected tiny standalone overfit approaches
- created a broader stage-2 hardcase refresh
- trained and promoted `stage2_hardcases_v3_bias`

Current outcome:
- strong improvement on the focused 8-claim support-bias packet
- much better protection against specific false-positive classes
- safer than earlier stance checkpoints

Current status:
- finished enough for runtime use
- still not perfect on all contradiction styles, but clearly better than before

### 3. Frontend and UX cleanup

The interface is substantially better than earlier versions.

Completed improvements:
- short-claim advisories
- blocking on too-short claims
- cleaned status row behavior
- matching button styling for run/cancel
- progress panel cleanup
- live timer in progress panel
- input lock during analysis
- explanation and summary rendering improvements
- cache-busting of frontend assets
- startup env/config reliability fixes

Current status:
- functionally complete
- not a project blocker anymore
- only incremental polish remains

### 4. Benchmarking and evaluation flow

The benchmarking and follow-up workflow is now far stronger than before.

Completed:
- 8-claim support-bias packet
- 30-claim benchmark artifacts
- 68-claim mixed benchmark flow
- 100-claim mixed seed flow
- checkability evaluation packet
- multilingual benchmark packet
- adjusted metrics excluding `blocked_not_checkable`
- benchmark builder helpers and follow-up docs

Current status:
- good enough to guide project decisions
- no longer guessing blindly

## What Was Explored But Not Promoted

### 1. Multilingual relevance training line (`v13`)

A lot of work was done here:
- broader relevance planning
- residual source-quality dataset design
- two-stage training flow
- converted multilingual stage
- native multilingual stage
- larger generated multilingual native data

What happened:
- training metrics improved
- but runtime benchmarks did not beat `v9_run1`
- in some cases performance regressed
- the multilingual slice improved only slightly and not reliably enough

Conclusion:
- `v13` remains experimental
- `v9_run1` stays as the runtime relevance checkpoint

Current status:
- paused
- not promoted

### 2. Tiny support-bias-only stance fine-tune

A very small support-bias packet was tried as a standalone stance training set.

Outcome:
- immediate overfitting
- not trustworthy as a replacement model

Conclusion:
- this line was superseded by the broader stage-2 residual refresh approach

### 3. Broad retrieval heuristics

There were attempts to improve evidence behavior through more global heuristics such as boosting certain evidence types more aggressively.

Outcome:
- some narrow gains
- broader regressions in benchmark behavior
- support-bias improvements became less stable in some experiments

Conclusion:
- broad heuristic tuning is not the right long-term path
- residual data + learned improvements are the better direction

## What Is Still In Progress

### 1. Evidence retrieval quality

This is the biggest remaining technical bottleneck.

Symptoms:
- `neutral_despite_evidence`
- weak or derivative sources beating decisive sources
- authoritative pages existing but not winning
- strong passages retrieved but not surviving selection

Impact:
- very high
- this is now the single biggest limiter of final verdict quality

Current status:
- diagnosed well
- not solved yet

### 2. Source selection

This is closely related to retrieval quality but deserves to be called out separately.

Problem:
- topical pages and derivative pages can outrank more authoritative or more claim-matching pages

This is especially harmful for:
- science facts
- geography claims
- government and institution claims
- comparison claims
- taxonomy and definition claims

Current status:
- residual datasets and planning exist
- no promoted runtime improvement yet

### 3. Multilingual checkability over-blocking

Claim-checkability improved substantially overall, but some multilingual factual claims can still be blocked or handled weakly.

Current status:
- identified as real
- not yet fully fixed

## What Still Needs to Start Properly

These are the next real workstreams that should be treated as project priorities:

1. Retrieval/source audit on recurring benchmark misses
2. Claim-level source-selection residual collection
3. Multilingual factual-claim checkability collection
4. Only then the next training pass, if justified by the evidence

This is the logic behind `REAL_BOTTLENECKS_PHASED_PLAN.md`.

## Incomplete Plans

The main unfinished plan is already documented in `REAL_BOTTLENECKS_PHASED_PLAN.md`.

Its unfinished parts are:
- retrieval audit on recurring neutral-despite-evidence misses
- source-selection residual growth
- multilingual wrongly-blocked claim collection
- next training decision after better data, not before

Additional partially complete but unfinished lines:
- multilingual relevance replacement for `v9_run1`
- broader multilingual runtime robustness
- retrieval/source-quality residual expansion at scale

## How This Affects the Project Goal

If the project goal is better product behavior for users:
- the system is already in a decent place
- claim junk filtering is much better
- support-bias risk is lower
- UX is stronger
- the stable runtime stack is usable

If the project goal is strong and reliable fact-check quality:
- the project is not finished
- the main blocker is no longer UI or checkability or even stance
- the main blocker is retrieval quality and source selection

In practice, the retrieval/source problem now has the highest effect on whether the project reaches its real goal.

## Current Completion Read

A fair current read is:

- front-door input quality / claim gating: strong
- stance safety / support-bias reduction: strong
- frontend usability: good
- benchmarking discipline: good
- relevance replacement experiments: explored, not successful enough
- retrieval/source-quality core problem: still open and high priority
- multilingual robustness: partially explored, not production-strong

## What Can Be Done To Make It Best-In-Class

If the project is to move from a strong prototype to a truly high-quality system, the next steps should be more deliberate and more data-driven than the earlier experimental loops.

### 1. Build a retrieval/source-quality residual program

This is the highest-value next move.

Needed:
- collect many recurring benchmark misses where the right source existed but did not win
- store claim + winning bad source + desired good source + decisive passage
- separate error families such as:
  - authoritative source lost to derivative source
  - decisive paragraph lost to topical paragraph
  - contradiction-bearing evidence failed to survive
  - numeric/comparison mismatch failed to rank correctly

Goal:
- create a larger residual set for relevance and source selection training/evaluation

### 2. Create a stronger source-quality preference layer

The system needs better learned preferences for:
- official / primary sources over derivative summaries
- decisive answer sentences over broad topical summaries
- contradiction-bearing passages for false claims
- entity- and relation-matching passages over loosely similar pages

This can be approached through:
- broader reranker training data
- pairwise preference training for better-vs-worse candidate evidence
- stronger post-retrieval ranking evaluation

### 3. Expand multilingual data the right way

Multilingual performance will not improve reliably without better data.

Needed:
- more native-script multilingual claim/evidence pairs
- more multilingual checkability examples
- more multilingual factual positives, not just translated news snippets
- more multilingual negatives that are realistic and hard

The right sequencing is:
- English / converted semantic stage
- native multilingual adaptation stage
- multilingual evaluation packet growth
- promote only if multilingual gains do not regress core English benchmarks

### 4. Improve checkability for multilingual factual claims

This should be treated as its own workstream, not assumed to be solved by relevance or stance.

Needed:
- collect wrongly blocked multilingual factual claims
- build a multilingual checkability residual packet
- retrain or adapt the checkability model with those examples
- benchmark top-level blocking behavior separately from verdict behavior

### 5. Expand benchmark coverage without losing discipline

The current benchmark infrastructure is much better than before, but it can still become stronger.

Needed:
- maintain stable core benchmark packets
- preserve a clean set of trusted result artifacts
- build category-level benchmark slices for:
  - science
  - geography
  - government / civic
  - myth / debunking
  - multilingual
  - comparison / numeric / date claims

Goal:
- stop optimizing blindly and know exactly which failure family moved

### 6. Keep the stable runtime frozen while experimentation continues

One of the most important process improvements now is discipline.

Best practice going forward:
- keep the current best runtime stack frozen
- run experiments off to the side
- only promote new checkpoints when they beat baseline on:
  - 30-claim benchmark
  - 68-claim benchmark
  - support-bias packet
  - multilingual packet, if multilingual is the purpose

This avoids destabilizing the system with attractive but misleading training metrics.

## Best-Case Endgame

If the project continues in the right direction, the strongest realistic endgame looks like this:

- stable claim-checkability gate with multilingual robustness
- safer stance model with fewer dangerous false positives
- relevance/source ranking that consistently prefers authoritative and decisive evidence
- reliable survival of contradiction-bearing evidence for false claims
- multilingual support that helps without harming the English baseline
- benchmark suite that clearly proves gains before promotion

That would turn the system from a strong prototype into a much more trustworthy fact-checking pipeline.

## Resume Point

If work resumes later, the best next step is not another broad training pass.
The best next step is:

1. continue from `REAL_BOTTLENECKS_PHASED_PLAN.md`
2. audit recurring retrieval/source failures
3. build the next residual dataset from those failures
4. train only after that data is strong enough

That is the highest-leverage path forward.
