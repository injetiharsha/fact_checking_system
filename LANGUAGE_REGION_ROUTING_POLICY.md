# Language And Region Routing Policy

Status: 2026-03-22

This note explains how the system should route retrieval when claims are not clean English global-fact claims.

## Core Principle

The system should be:

- language-aware
- region-aware
- internet-first
- conservative when locality is unclear

The system should **auto-detect first**, not rely on a giant manually hardcoded country-by-country routing table.

## Intended Routing Order

For each claim:

1. detect language
2. preserve the original claim text
3. translate to English for general reasoning compatibility
4. infer likely locality from both:
   - translated claim text
   - original-language claim text
5. build search queries using:
   - translated claim
   - original claim
   - domain/context hints
   - region hints if confidence is high enough
6. keep local-language retrieval as a fallback or supplement when English retrieval is weak or locality is explicit

## What Region Signals Matter

Strong locality signals:

- explicit state or country names
- city names strongly tied to a region
- original-language scripts
- local program names
- local administrative language
- local domain hints

Weak locality signals:

- short acronyms like `AP`, `UP`, `TN`
- vague phrases like `farmers`, `scheme`, `deadline`
- generic translated phrasing after original-language information is lost

Weak signals should not be trusted alone.

## Routing Policy

### When locality is clear

If the claim clearly points to a region:

- add region-aware search terms
- add original-language search queries
- add trusted local source/domain hints
- prioritize official or local authoritative sources before broad generic ones

Example:

- Telugu claim with strong Andhra Pradesh cues
- use Telugu query variants
- use Andhra Pradesh local source hints

### When locality is unclear

If the system cannot infer region confidently:

- keep search broad
- avoid overfitting to a guessed region
- do not assume a local acronym belongs to one place without evidence

### When English search is weak

If English retrieval looks weak or generic:

- retry with original-language query
- retry with local-language media domains if region confidence is sufficient
- keep both local and broad evidence visible in trace output

## Why This Policy

This approach is better than manually encoding every region because it:

- scales better
- avoids excessive brittle heuristics
- works beyond India
- preserves local-language evidence paths
- still stays conservative when the region is ambiguous

## Current Implementation Status

Partially implemented:

- language detection
- original-language preservation
- English translation for reasoning path
- India state alias detection
- some language-locality hints
- original-language query fallback
- local-domain search hints for selected Indian states

Not yet fully implemented:

- broad world-region routing coverage
- strong locality confidence scoring for all languages
- official-source registries for many non-Indian regions
- multilingual stance handling strong enough to match improved retrieval

## Practical Rule Going Forward

The system should continue to evolve toward:

- **auto-detected language + region routing**

and not toward:

- a manually expanded giant static routing table for every region

## Current Best Interpretation

Use this mental model:

- default: broad/global retrieval
- if language or geography clearly indicates locality: widen into local-language and local-region retrieval
- if locality is uncertain: stay conservative

That is the most scalable and least brittle path.
