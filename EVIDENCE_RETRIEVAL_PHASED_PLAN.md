# Evidence Retrieval Phased Plan

This file is the working tracker for improving evidence retrieval in this project without paid APIs.

Goal:
- improve retrieval quality
- stay budget-friendly
- move toward a local RAG-style pipeline
- avoid marking progress as done until each phase meets explicit completion checks

How to use this file:
- update the `Status` for each phase as work progresses
- only mark a phase `Completed` when every completion check for that phase is true
- if a phase is partly implemented, keep it as `In Progress`

Status legend:
- `Not Started`
- `In Progress`
- `Completed`
- `Blocked`

---

## Phase 1: Better Extraction and Observability

Status: `Not Started`

Purpose:
- improve raw page extraction quality before changing architecture
- make failures visible so we know whether search, fetch, extraction, or filtering is failing

Tasks:
- replace paragraph-only extraction in `evidence/scraper.py`
- replace paragraph-only extraction in `ingestion/webpage.py`
- use `trafilatura` as the primary extractor
- keep BeautifulSoup as a fallback extractor
- add retry and timeout handling for page fetches
- add simple local caching for fetched or extracted pages
- log extraction method used, word count, and rejection reason
- filter obvious junk pages early such as search results, tag pages, and category pages

Completion checks:
- `trafilatura` is integrated into both `evidence/scraper.py` and `ingestion/webpage.py`
- fallback extraction still works when `trafilatura` fails
- extraction logs include method, word count, and failure or reject reason
- repeated fetches of the same page can reuse cached output
- benchmark runs show fewer empty or near-empty scraped pages than before

Evidence to record before marking completed:
- note the files changed
- note one benchmark or sample run result
- note whether empty-page rate dropped

Notes:
- do not move to `Completed` just because extraction code was added
- it must be tested in the actual pipeline

---

## Phase 2: Better Free Search and Candidate Ranking

Status: `In Progress`

Purpose:
- improve the quality of URLs entering the scraper
- reduce noise from weak or irrelevant search results

Tasks:
- improve query building in `evidence/router.py`
- expand queries using entities, years, and claim type
- add source-focused variants such as `site:wikipedia.org`, `site:.gov`, `site:.edu`, `site:who.int`, `site:worldbank.org`
- rank search candidates before scraping
- score candidates using title overlap, year match, domain quality, and numeric match when relevant
- reduce scrape fan-out so only top candidates are fetched
- log which search query produced each selected URL

Completion checks:
- the router generates multiple targeted query variants for eligible claims
- the router ranks candidate URLs before scraping
- the number of scraped URLs per claim is lower or controlled more tightly than today
- logs show why high-ranked URLs were selected
- benchmark or debug runs show a better ratio of usable evidence to scraped pages

Evidence to record before marking completed:
- note sample queries generated
- note how many URLs were scraped before and after
- note whether usable evidence count improved

Notes:
- keep this phase free and local-first
- DuckDuckGo HTML can remain for now, but candidate ranking must improve
- Current repo state:
  - multi-query generation exists in `evidence/router.py`
  - context-shaped query expansion exists
  - routing/debug output already exposes `search_queries`
  - pre-scrape candidate scoring and ranking are still missing

---

## Phase 3: Local Trusted Corpus and FAISS Index

Status: `Not Started`

Purpose:
- build a reusable local evidence base
- reduce dependence on live web search for repeated factual claims

Tasks:
- create a corpus builder for trusted sources
- include sources like Wikipedia, WHO, World Bank, OECD, UN, and high-value government pages
- chunk documents into overlapping passages
- store chunk metadata such as source, domain, url, title, and date when available
- generate embeddings locally
- build a FAISS index for passage retrieval
- add a local retrieval path before live web search

Completion checks:
- a local corpus builder script exists and can run successfully
- trusted source passages are saved in a consistent format
- a FAISS index can be built and loaded locally
- a claim can retrieve top passages from the local index
- the pipeline can use local retrieval before falling back to live web search

Evidence to record before marking completed:
- note corpus location
- note embedding model used
- note at least one example claim and the passages retrieved from FAISS

Notes:
- start with a small trusted corpus first
- do not wait for a huge dataset before integrating the retrieval path

---

## Phase 4: Multi-Passage Evidence Instead of Early Single-Sentence Compression

Status: `In Progress`

Purpose:
- reduce verdict failures caused by selecting one weak sentence from a useful document

Tasks:
- stop collapsing documents to only one sentence too early in `pipeline/claim_pipeline.py`
- retrieve multiple chunks or passages per source
- score several passages per document
- run stance detection on more than one passage
- aggregate at the document level before final verdict aggregation

Completion checks:
- each document can contribute multiple candidate passages
- stance detection runs on more than one passage for at least some sources
- document-level aggregation exists before final verdict aggregation
- benchmark results show fewer failures caused by bad sentence selection

Evidence to record before marking completed:
- note how many passages per document are considered
- note one claim where multi-passage retrieval improved the result

Notes:
- this phase is important because better scraping alone will not fix brittle sentence selection
- Current repo state:
  - `pipeline/claim_pipeline.py` already keeps more than one top sentence candidate
  - but the system still collapses too early to sentence-level evidence
  - document-level multi-passage aggregation is not implemented yet

---

## Phase 5: Claim-Type-Aware Retrieval

Status: `In Progress`

Purpose:
- make retrieval smarter for different fact-checking patterns

Tasks:
- route numerical claims toward structured sources and passages with matching numbers or units
- route historical claims toward year-rich or event-rich passages
- route entity-property claims toward encyclopedic or institutional sources
- strengthen India-specific routing using existing domain hints and source registries
- use claim context and claim type to influence ranking

Completion checks:
- retrieval ranking changes based on claim type or context
- numerical claims prefer sources with matching numbers, units, or years
- India-specific factual claims use local trusted source hints
- logs make the routing decision visible

Evidence to record before marking completed:
- note one numerical claim example
- note one historical or entity-property claim example
- note how retrieval behavior changed

Notes:
- this phase should build on the claim classification work already present in the repo
- Current repo state:
  - claim type classifier exists
  - context classifier exists
  - India state/local source hints exist
  - soft retrieval query shaping is already wired in
  - ranking still does not strongly adapt by claim category

---

## Phase 6: Optional Browser Rendering Fallback

Status: `Not Started`

Purpose:
- recover text from JS-heavy pages without turning browser automation into the default path

Tasks:
- add Playwright as a fallback only
- trigger fallback when normal extraction returns too little text or obvious shell HTML
- limit browser rendering to a small number of top-ranked pages
- cache rendered output
- log when rendering was triggered and whether it improved extraction

Completion checks:
- browser rendering is not the default fetch path
- fallback triggers only for pages that fail normal extraction checks
- rendered output is cached
- there is at least one verified example where rendering recovered useful evidence

Evidence to record before marking completed:
- note trigger conditions
- note one successful JS-heavy page example
- note impact on latency

Notes:
- skip this phase unless earlier cheaper improvements are already in place

---

## Phase 7: Continuous Corpus Growth From Successful Runs

Status: `Not Started`

Purpose:
- make the system improve over time without paying for external search

Tasks:
- save strong evidence passages from successful live retrieval runs
- deduplicate by normalized URL and passage content
- attach metadata and retrieval quality signals
- update the local corpus periodically
- rebuild or incrementally refresh the FAISS index
- keep low-quality or noisy passages out of the corpus

Completion checks:
- successful runs can contribute new passages to the local corpus
- duplicate passages are filtered out
- the FAISS index can be refreshed after corpus growth
- local retrieval coverage improves over time for repeated claim patterns

Evidence to record before marking completed:
- note how many passages were added
- note how deduplication is handled
- note one example where a later run benefited from saved evidence

Notes:
- this phase is what makes the system cheaper and stronger over time

---

## Current Recommended Order

1. Phase 1
2. Phase 2
3. Phase 4
4. Phase 5
5. Phase 3
6. Phase 7
7. Phase 6

Reason:
- Phase 1 and Phase 2 address the current biggest live bottlenecks first
- Phase 4 is higher ROI than FAISS right now because sentence collapse is still hurting current evidence use
- Phase 5 should build on the claim type and context hooks that already exist
- Phase 3 becomes more valuable after the live retrieval path is cleaner
- Phase 7 compounds improvements after retrieval quality is worth preserving
- Phase 6 remains optional and should stay limited

---

## Progress Summary

Use this section as the quick status board.

| Phase | Name | Status | Last Checked | Notes |
| --- | --- | --- | --- | --- |
| 1 | Better Extraction and Observability | Not Started | 2026-03-14 | Raw extraction is still mostly paragraph-based; no `trafilatura` yet |
| 2 | Better Free Search and Candidate Ranking | In Progress | 2026-03-14 | Query expansion exists; strong pre-scrape candidate ranking is still missing |
| 3 | Local Trusted Corpus and FAISS Index | Not Started | 2026-03-14 | No local corpus or FAISS path exists yet |
| 4 | Multi-Passage Evidence | In Progress | 2026-03-14 | Top-2 sentence selection exists; true multi-passage/document-level aggregation does not |
| 5 | Claim-Type-Aware Retrieval | In Progress | 2026-03-14 | Claim type, context, and India-local hints exist; retrieval ranking is still shallow |
| 6 | Optional Browser Rendering Fallback | Not Started | - | - |
| 7 | Continuous Corpus Growth | Not Started | - | - |

---

## Phase Review Template

Use this before changing a phase to `Completed`.

### Review Checklist

- What changed?
- Which files were modified?
- What tests, benchmark runs, or sample claims were used?
- Which completion checks are satisfied?
- What is still missing?
- Should the phase remain `In Progress` or move to `Completed`?

### Completion Rule

If any completion check is still unverified, do not mark the phase as `Completed`.
