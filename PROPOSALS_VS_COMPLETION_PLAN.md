# Proposals vs Completion Plan

## Why This Document Exists

This document compares:

1. the project-improvement proposals that were suggested as direct fixes
2. the broader completion plan needed to turn the system into a genuinely strong fact-checking project

The goal is not to dismiss the proposed fixes. Many of them are useful. The goal is to explain:
- what those fixes can improve
- why they are not enough by themselves
- what still has to be done to actually complete the project

## The Proposed Fixes

The suggested fixes were:

1. Let the LLM verifier fire more often
2. Lower sentence-selection thresholds so decisive short evidence is less likely to be dropped
3. Add better comparison/superlative rescue logic in stance handling
4. Make trusted-source bonuses conditional on BM25 quality
5. Bypass the trained multilingual checkability model for non-Latin scripts and use heuristics instead
6. Loosen the session retrieval cache so it actually reuses more evidence
7. Disable or restrict logic-engine support injection for misinformation-sensitive claims

These are all reasonable ideas. Some are strong short-term wins. But they do not fully solve the project by themselves.

## What Your Proposed Fixes Would Help With

### 1. Broader LLM verifier triggering

This is one of the best short-term ideas.

What it helps:
- borderline `TRUE` or `FALSE` verdicts that should get a second opinion
- dangerous false positives where the current system is too confident too early
- myth/debunking style claims where evidence is mixed or misleading

Why it helps:
- the LLM verifier is already connected and available
- the current `neutral_only` policy underuses it
- some risky support/refute cases never get reviewed

Expected effect:
- likely reduction in some false positives
- especially on claims where the evidence mix is not clearly trustworthy

### 2. Lowering strong/soft evidence thresholds

This addresses a real issue.

What it helps:
- short, decisive factual evidence that currently gets demoted
- `neutral_despite_evidence` failures where the right sentence exists but is treated as too weak

Why it helps:
- the current selection logic can prefer longer topical paragraphs over direct factual statements
- some true claims are being lost because the best answer sentence is short

Expected effect:
- some true claims may flip from `NEUTRAL` to correct verdicts

### 3. Better comparison/superlative rescue in stance logic

This is a useful narrow fix.

What it helps:
- claims like Amazon vs Nile
- largest/deepest/farthest style factual disputes
- some taxonomy/comparison failures where contradiction is expressed indirectly

Why it helps:
- the current rescue logic is narrower than the kinds of evidence actually appearing in the wild

Expected effect:
- fewer wrong verdicts on a specific failure family

### 4. Conditional source bonus in candidate scoring

This is one of the stronger retrieval-side ideas.

What it helps:
- weak trusted pages beating strong but more relevant evidence
- derivative authoritative pages outranking better-matching content for the claim

Why it helps:
- authority should not override relevance when textual match is weak
- the current flat source bonus can be too blunt

Expected effect:
- better balance between source trust and textual fit

### 5. Multilingual checkability bypass for non-Latin scripts

This is a practical short-term safeguard.

What it helps:
- native-script claims being wrongly blocked by an English-shaped trained classifier

Why it helps:
- the checkability model was trained mostly on English-oriented data
- heuristic fallback may be safer than a badly calibrated multilingual classification on scripts it barely saw

Expected effect:
- fewer wrongful blocks on native-script factual claims

### 6. Looser session cache eligibility

This is useful, but more for efficiency than core correctness.

What it helps:
- repeated similar claims
- fewer repeated retrieval passes for near-paraphrases

Expected effect:
- some efficiency gains
- some reuse gains
- but not a major fix for benchmark quality by itself

### 7. Logic-engine guard for misinformation-sensitive claims

This is a good safety-oriented fix.

What it helps:
- cases where a noisy support signal gets amplified into a wrong final verdict
- myth/debunking claims where synthetic consensus can be misleading

Expected effect:
- fewer dangerous wrong `TRUE` verdicts on misinformation-sensitive claims

## Why These Fixes Are Not Enough By Themselves

The short answer is:

They mostly improve symptoms, guardrails, and narrow failure families.
They do not fully solve the core retrieval and evidence-selection problem.

### Reason 1: They are mostly tactical, not structural

Most of the proposed fixes are threshold, gating, or policy changes.
Those can improve behavior, but they do not fundamentally give the system a much better ability to:
- retrieve the right pages
- prefer the best source for the claim
- keep the decisive passage alive all the way through verdict formation

That deeper ability usually needs:
- better training data
- better source-selection preferences
- better retrieval/reranking behavior

### Reason 2: Several of them are heuristic or rule-shaped

Even the good ones have a limit.

Examples:
- comparison rescue rules help specific patterns, not the whole space of contradiction
- multilingual checkability bypass helps avoid a failure, but does not create a genuinely multilingual claim-checkability model
- threshold lowering may help some true claims but can also reintroduce noisy weak evidence

These are good tactical patches, but they are not the same as building a robust system.

### Reason 3: They do not build enough new learning signal

A complete project needs more than better flags and thresholds.
It needs stronger data for the model to learn from.

Without better residual data, the system will keep rediscovering the same families of failure:
- authoritative source lost to derivative page
- contradiction-bearing passage dropped
- short direct answer underweighted
- multilingual factual claim handled weakly

### Reason 4: Some proposed fixes can trade one error for another

Examples:
- lowering evidence thresholds can improve recall, but also boost low-quality snippets
- firing the LLM verifier more often can reduce some false positives, but may also increase cost and over-neutralization
- disabling logic-engine support in some cases can improve safety, but may also remove helpful aggregation in benign factual cases

So even the good ideas need careful benchmark validation.

## What Is Still Needed To Complete The Project

To make the project complete, the system needs more than tactical fixes. It needs a more finished architecture across five areas.

### 1. A complete input-gating layer

The project already made strong progress here.
But completion requires:
- trained claim-checkability in runtime
- multilingual-safe fallback behavior
- multilingual residual data expansion
- reliable handling of short claims, vague claims, opinions, and personal statements

Why this matters:
- the project should not waste retrieval and model budget on text that is not fact-checkable
- this makes the system safer and more product-ready

### 2. A stronger retrieval and source-selection layer

This is the biggest remaining blocker.

Completion requires:
- better authoritative-source selection
- better claim-matching page ranking
- better survival of decisive factual passages
- better handling of contradiction-bearing evidence for false claims
- broader residual data for relevance/source preference training

Why this matters:
- this is the real bottleneck behind many `neutral_despite_evidence` failures
- this is also where many wrong-source/wrong-passage verdicts come from
- without solving this, the project will remain a strong prototype rather than a strong final system

### 3. A strong stance/verdict layer

The project is already much better here.

Completion requires:
- keeping the current safer stance baseline
- adding new residual stance data only when a real new failure family is found
- preventing unsafe synthetic support amplification on misinformation-sensitive claims

Why this matters:
- verdict quality depends on robust support/refute interpretation
- false positives are especially harmful in a fact-checking project

### 4. A clean explanation and UX layer

This is mostly in good shape now.

Completion requires:
- readable summaries
- structured support/refute/neutral explanation sections
- clear source display
- stable progress behavior
- safe cancel/lock/retry flow

Why this matters:
- a fact-checking system must explain itself clearly, not just classify

### 5. A strict benchmark and promotion layer

Completion requires:
- stable benchmark packets
- stable metric summaries
- promotion rules for new checkpoints
- side-by-side comparisons before any promotion

Why this matters:
- otherwise the project will keep promoting models that look good in training but regress in runtime
- this already happened with the multilingual relevance `v13` line

## What I Propose As The Complete Path

The completion plan is not "ignore your fixes." It is:

1. use the best short-term fixes where they are safe and high-value
2. do not mistake them for final completion
3. keep building the stronger retrieval/source-selection and multilingual data foundations

### Phase 1: Safe short-term improvements

These are worth testing or adopting soon:
- broader LLM verifier triggering for risky low-confidence cases
- logic-engine guard on misinformation-sensitive claims
- multilingual checkability bypass for native-script claims until the model is stronger
- conditional trusted-source bonus based on BM25 quality

Why this phase helps:
- it can reduce dangerous errors relatively quickly
- it improves safety without waiting for major retraining

### Phase 2: Retrieval/source residual program

This is the core completion phase.

Needed:
- collect recurring failures where the right source existed but did not win
- collect claim + bad source + desired good source + decisive passage
- build a larger residual dataset for source-selection and evidence survival
- retrain or retune relevance/reranking only after this dataset is strong enough

Why this phase matters most:
- it attacks the root of the biggest remaining project bottleneck
- it is the highest-leverage step toward a truly strong fact-checking system

### Phase 3: Multilingual robustness

Needed:
- multilingual claim-checkability residual data
- native-script multilingual factual positives and negatives
- multilingual relevance/source preference examples
- promotion only if multilingual gains do not damage English benchmarks

Why this phase matters:
- a multilingual project cannot rely forever on English-shaped models plus heuristics
- proper multilingual support requires data and evaluation, not just fallback rules

### Phase 4: Final hardening

Needed:
- lock a best-known stack
- preserve only qualified result artifacts
- keep benchmark packets stable
- formalize model promotion criteria
- make deployment/runtime behavior predictable

Why this phase matters:
- it turns the system from "many experiments" into a maintainable project

## Why This Completion Plan Would Work Better

### 1. It addresses the root bottleneck, not just edge behaviors

The proposed fixes help edge behaviors and narrow failure families.
The completion plan specifically targets the biggest remaining root problem:
- retrieval quality
- source ranking
- decisive evidence survival

That is why it has higher project-wide impact.

### 2. It uses your fixes where they help, but does not over-trust them

This plan still values your proposals.
It simply puts them in the right place:
- as short-term safety and quality improvements
- not as substitutes for the deeper unfinished work

### 3. It is benchmark-driven

The project already learned the hard lesson that good training metrics are not enough.
A completion plan that requires benchmark promotion gates is much more likely to produce real progress.

### 4. It scales better

Rule patches and threshold tweaks eventually become hard to manage.
Residual datasets, better training data, and controlled benchmark gating scale better as the project grows.

## Bottom Line

Your proposed fixes are useful.
Several of them should probably be tested or adopted.
But they do not complete the project on their own.

They mostly help with:
- short-term safety
- tactical retrieval improvements
- narrow failure families
- multilingual stopgaps

The project becomes complete only when those tactical gains are combined with:
- stronger retrieval/source selection
- stronger evidence survival
- better multilingual data
- stable benchmark-driven checkpoint promotion

That is why the completion plan is bigger than the individual fixes.

## Practical Takeaway

Best reading:
- your proposals = important short-term improvement ideas
- my proposal = the full path needed to make the project actually complete

The right strategy is not to choose one or the other.
It is:
- use the best of your proposals as short-term stabilizers
- keep working on the deeper retrieval/source-quality completion path

That combination is what has the best chance of turning this into a genuinely strong project.
