import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FOCUSED_CLAIMS = [
    {"claim": "The moon landing was faked", "expected": "FALSE"},
    {"claim": "Climate change is a hoax", "expected": "FALSE"},
    {"claim": "Drinking bleach cures COVID-19", "expected": "FALSE"},
    {"claim": "Mars has two moons", "expected": "TRUE"},
    {"claim": "The Berlin Wall fell in 1989", "expected": "TRUE"},
    {"claim": "The United Nations was founded after World War II", "expected": "TRUE"},
    {"claim": "Humans can breathe in space without equipment", "expected": "FALSE"},
    {"claim": "Octopuses have three hearts", "expected": "TRUE"},
]


def _load_completed(output_path: Path):
    completed = {}
    if not output_path.exists():
        return completed
    for line in output_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        claim = row.get("claim")
        if claim:
            completed[claim] = row
    return completed


def _append_result(output_path: Path, row: dict):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_summary(summary_path: Path, rows: list[dict]):
    total = len(rows)
    correct = sum(1 for row in rows if row.get("ok"))
    summary = {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total, 3) if total else 0.0,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "claims": rows,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _run_claim(claim: str):
    start = time.time()
    child_env = os.environ.copy()
    child_env["PYTHONPATH"] = str(REPO_ROOT)
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "run_single_claim.py"), claim]
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=child_env,
        cwd=str(REPO_ROOT),
    )
    elapsed = round(time.time() - start, 3)
    if completed.returncode != 0:
        return {
            "ok": False,
            "elapsed": elapsed,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "error": f"subprocess_exit_{completed.returncode}",
        }
    lines = [line for line in (completed.stdout or "").splitlines() if line.strip()]
    payload = None
    for line in reversed(lines):
        try:
            payload = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    if payload is None:
        return {
            "ok": False,
            "elapsed": elapsed,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "error": "invalid_json_output",
        }
    payload["elapsed"] = elapsed
    payload["stderr"] = completed.stderr
    payload["ok"] = True
    return payload


def main():
    parser = argparse.ArgumentParser(description="Run focused claims sequentially with resumable output.")
    parser.add_argument("--output", default="logs/focused_claims_results.jsonl")
    parser.add_argument("--summary", default="logs/focused_claims_summary.json")
    parser.add_argument("--force", action="store_true", help="Ignore existing output and rerun all claims.")
    args = parser.parse_args()

    output_path = Path(args.output)
    summary_path = Path(args.summary)

    if args.force and output_path.exists():
        output_path.unlink()

    completed = _load_completed(output_path)

    rows = []
    for item in FOCUSED_CLAIMS:
        claim = item["claim"]
        expected = item["expected"]

        if claim in completed:
            row = completed[claim]
            rows.append(row)
            print(f"Skipping completed claim: {claim}")
            continue

        print("\n==============================")
        print("Claim:", claim)
        print("Expected:", expected)

        run_result = _run_claim(claim)
        elapsed = run_result.get("elapsed", 0.0)
        response = run_result.get("pipeline_output") if run_result.get("ok") else {
            "error": run_result.get("error"),
            "stderr": run_result.get("stderr"),
        }
        result_row = run_result.get("result_row", {}) if run_result.get("ok") else {}
        verdict = result_row.get("final_verdict", "ERROR" if not run_result.get("ok") else "NEUTRAL")
        confidence = result_row.get("confidence", 0.0)
        transparency = result_row.get("transparency", {}) if isinstance(result_row, dict) else {}
        output_row = {
            "claim": claim,
            "expected": expected,
            "verdict": verdict,
            "confidence": confidence if run_result.get("ok") else 0.0,
            "ok": run_result.get("ok") and verdict == expected,
            "elapsed_seconds": elapsed,
            "retrieval_version": transparency.get("retrieval_version"),
            "reranker_provider": transparency.get("reranker_provider"),
            "search_queries": list(result_row.get("search_queries", [])) if isinstance(result_row, dict) else [],
            "pipeline_output": response,
            "error": None if run_result.get("ok") else run_result.get("error"),
        }
        _append_result(output_path, output_row)
        rows.append(output_row)
        print("Verdict:", verdict)
        print("Confidence:", confidence)
        print("Elapsed:", elapsed, "sec")
        if not run_result.get("ok"):
            print("Subprocess error:", run_result.get("error"))

    summary = _write_summary(summary_path, rows)
    print("\n==============================")
    print("Focused run complete")
    summary_text = json.dumps(summary, ensure_ascii=False, indent=2)
    safe_summary = summary_text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace")
    print(safe_summary)


if __name__ == "__main__":
    main()


