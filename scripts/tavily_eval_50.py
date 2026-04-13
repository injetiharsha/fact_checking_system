import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

try:
    from tavily import TavilyClient
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: tavily-python. Install with `.\\.venv\\Scripts\\python.exe -m pip install tavily-python`."
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

DEFAULT_CLAIMS_FILE = ROOT / "benchmark_claims" / "robust_mixed_50_v2.json"
DEFAULT_OUTPUT = ROOT / "logs" / "tavily_eval_50.json"

OFFICIAL_DOMAIN_HINTS = {
    "space": ["nasa.gov"],
    "astronomy": ["nasa.gov"],
    "health": ["who.int", "cdc.gov", "nih.gov"],
    "public_health": ["who.int", "cdc.gov", "nih.gov"],
    "india_live": ["pib.gov.in", "rbi.org.in", "isro.gov.in", "eci.gov.in", "indianrailways.gov.in"],
    "finance": ["rbi.org.in", "worldbank.org", "oecd.org"],
    "economics": ["rbi.org.in", "worldbank.org", "oecd.org"],
    "geography": ["britannica.com", "wikipedia.org"],
    "science": ["nasa.gov", "britannica.com", "wikipedia.org"],
}

EXCLUDE_DOMAIN_HINTS = [
    "prepp.in",
    "testbook.com",
    "shaalaa.com",
    "careers360.com",
    "vedantu.com",
    "byjus.com",
]


def load_claims(path: Path):
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Claims file must be a JSON list.")
    loaded = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        claim = str(row.get("claim") or "").strip()
        if not claim:
            continue
        loaded.append(
            {
                "claim": claim,
                "expected_verdict": row.get("expected_verdict"),
                "language": row.get("language"),
                "category": row.get("category"),
            }
        )
    return loaded


def infer_topic(row):
    category = str(row.get("category") or "").strip().lower()
    claim = str(row.get("claim") or "").lower()
    if category in {"india_live"}:
        return "news"
    if category in {"finance", "economics"} or "bank" in claim or "currency" in claim:
        return "finance"
    return "general"


def infer_time_range(row):
    category = str(row.get("category") or "").strip().lower()
    claim = str(row.get("claim") or "").lower()
    temporal_markers = ("today", "yesterday", "this week", "recently", "latest", "2026", "2025")
    if category == "india_live" or any(marker in claim for marker in temporal_markers):
        return "month"
    return None


def infer_include_domains(row):
    category = str(row.get("category") or "").strip().lower()
    domains = list(OFFICIAL_DOMAIN_HINTS.get(category, []))
    claim = str(row.get("claim") or "").lower()
    if "isro" in claim:
        domains.append("isro.gov.in")
    if "reserve bank of india" in claim or "rbi" in claim:
        domains.append("rbi.org.in")
    if "mars" in claim or "moon" in claim or "planet" in claim:
        domains.append("nasa.gov")
    if "covid" in claim or "vaccine" in claim or "bleach" in claim:
        domains.extend(["who.int", "cdc.gov"])
    deduped = []
    seen = set()
    for domain in domains:
        normalized = str(domain or "").strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def build_search_kwargs(row, depth, max_results):
    kwargs = {
        "query": row["claim"],
        "search_depth": depth,
        "max_results": max_results,
        "include_answer": "advanced",
        "topic": infer_topic(row),
    }
    include_domains = infer_include_domains(row)
    if include_domains:
        kwargs["include_domains"] = include_domains
        kwargs["exclude_domains"] = EXCLUDE_DOMAIN_HINTS
    time_range = infer_time_range(row)
    if time_range:
        kwargs["time_range"] = time_range
    return kwargs


def run_search(client, row, depth, max_results):
    kwargs = build_search_kwargs(row, depth=depth, max_results=max_results)
    started = time.time()
    response = client.search(**kwargs)
    elapsed = round(time.time() - started, 3)
    return {
        "mode": "search",
        "elapsed_seconds": elapsed,
        "request": kwargs,
        "answer": response.get("answer"),
        "results": response.get("results", []),
    }


def run_extract(client, search_payload, query):
    urls = [row.get("url") for row in (search_payload.get("results") or [])[:3] if row.get("url")]
    if not urls:
        return {"mode": "extract", "elapsed_seconds": 0.0, "urls": [], "response": None}
    started = time.time()
    response = client.extract(urls=urls, query=query)
    elapsed = round(time.time() - started, 3)
    return {
        "mode": "extract",
        "elapsed_seconds": elapsed,
        "urls": urls,
        "response": response,
    }


def run_crawl(client, seed_url, query, limit, max_depth, max_breadth, extract_depth):
    if not seed_url:
        return {"mode": "crawl", "elapsed_seconds": 0.0, "url": None, "response": None}
    started = time.time()
    response = client.crawl(
        url=seed_url,
        instructions=query,
        limit=limit,
        max_depth=max_depth,
        max_breadth=max_breadth,
        extract_depth=extract_depth,
    )
    elapsed = round(time.time() - started, 3)
    return {
        "mode": "crawl",
        "elapsed_seconds": elapsed,
        "url": seed_url,
        "response": response,
    }


def main():
    parser = argparse.ArgumentParser(description="Standalone Tavily evaluation on the 50-claim packet.")
    parser.add_argument("--claims-file", default=str(DEFAULT_CLAIMS_FILE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--search-depth", default="advanced")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--modes", default="search,extract", help="Comma-separated: search,extract,crawl")
    parser.add_argument("--crawl-limit", type=int, default=5)
    parser.add_argument("--crawl-max-depth", type=int, default=2)
    parser.add_argument("--crawl-max-breadth", type=int, default=4)
    parser.add_argument("--crawl-extract-depth", default="advanced")
    args = parser.parse_args()

    api_key = (os.getenv("TAVILY_API_KEY") or "").strip()
    if not api_key:
        raise SystemExit("Missing TAVILY_API_KEY in .env")

    client = TavilyClient(api_key=api_key)
    all_claims = load_claims(Path(args.claims_file))
    start_index = max(0, int(args.offset))
    end_index = start_index + max(1, args.limit)
    claims = all_claims[start_index:end_index]
    requested_modes = {item.strip().lower() for item in args.modes.split(",") if item.strip()}

    rows = []
    overall_start = time.time()
    for idx, row in enumerate(claims, start=start_index + 1):
        claim = row["claim"]
        print(f"[{idx}/{len(all_claims)}] {claim}")
        out = {
            "claim": claim,
            "expected_verdict": row.get("expected_verdict"),
            "language": row.get("language"),
            "category": row.get("category"),
            "topic": infer_topic(row),
            "include_domains": infer_include_domains(row),
            "time_range": infer_time_range(row),
        }

        search_payload = None
        if "search" in requested_modes or "extract" in requested_modes or "crawl" in requested_modes:
            search_payload = run_search(client, row, depth=args.search_depth, max_results=args.max_results)
            out["search"] = search_payload

        if "extract" in requested_modes:
            out["extract"] = run_extract(client, search_payload or {}, claim)

        if "crawl" in requested_modes:
            top_url = None
            if search_payload:
                for candidate in search_payload.get("results") or []:
                    if candidate.get("url"):
                        top_url = candidate["url"]
                        break
            out["crawl"] = run_crawl(
                client,
                seed_url=top_url,
                query=claim,
                limit=args.crawl_limit,
                max_depth=args.crawl_max_depth,
                max_breadth=args.crawl_max_breadth,
                extract_depth=args.crawl_extract_depth,
            )

        rows.append(out)
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    payload = {
        "claims_file": str(Path(args.claims_file)),
        "offset": start_index,
        "count": len(rows),
        "modes": sorted(requested_modes),
        "search_depth": args.search_depth,
        "max_results": args.max_results,
        "total_elapsed_seconds": round(time.time() - overall_start, 3),
        "results": rows,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
