import argparse
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = REPO_ROOT / "logs"
LEDGER_JSON = LOGS_DIR / "residual_ledger.json"
LEDGER_MD = REPO_ROOT / "RESIDUAL_LEDGER.md"

RECOMMENDED_STACK = {
    "ENABLE_TRAINED_STANCE": "1",
    "STANCE_CHECKPOINT": "checkpoints/stance/v2_run1",
    "ENABLE_TRAINED_RELEVANCE": "1",
    "RELEVANCE_CHECKPOINT": "checkpoints/relevance/v9_run1",
    "ENABLE_RETRIEVAL_V2": "0",
    "ENABLE_VERIFIER_V2": "0",
    "ENABLE_LLM_VERIFIER": "1",
    "LLM_VERIFIER_POLICY": "neutral_only",
    "BENCHMARK_MAX_CONCURRENT": "2",
}

BATCHES = {
    "baseline_30claim": {
        "claims_file": None,
        "filename": "baseline_30claim.json",
    },
    "multilingual_regression": {
        "claims_file": "benchmark_claims/multilingual_regression_batch_v2.json",
        "filename": "multilingual_regression.json",
    },
    "fresh_realtime": {
        "claims_file": "benchmark_claims/fresh_realtime_batch_2026-03-22.json",
        "filename": "fresh_realtime.json",
    },
}

FAILURE_TO_PRIMARY_CAUSE = {
    "neutral_despite_evidence": "relevance_ranking",
    "insufficient_evidence": "retrieval_source_quality",
    "false_positive_support_bias": "semantic_relation_handling",
    "false_positive_numeric": "semantic_relation_handling",
    "false_positive_general": "semantic_relation_handling",
    "false_negative_refute_bias": "aggregation_or_passage_collapse",
    "false_negative_general": "stance_only",
    "false_negative_numeric": "stance_only",
    "other": "stance_only",
}


def now_stamp():
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def infer_stack_label(cli_stack_label=None):
    if cli_stack_label:
        return cli_stack_label
    if all(os.getenv(key) == value for key, value in RECOMMENDED_STACK.items()):
        return "recommended_v9"
    return "custom_stack"


def check_env_matches_recommended():
    mismatches = []
    for key, value in RECOMMENDED_STACK.items():
        current = os.getenv(key)
        if current != value:
            mismatches.append((key, current, value))
    return mismatches


def run_benchmark(batch_name, output_path: Path):
    batch = BATCHES[batch_name]
    cmd = [sys.executable, "benchmark_multi_test.py", "--output", str(output_path)]
    if batch["claims_file"]:
        cmd.extend(["--claims-file", batch["claims_file"]])
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)



def infer_run_validity(metrics, validity):
    if validity and ("is_valid_comparison" in validity or "status" in validity):
        return validity
    total = int(metrics.get("total_claims", 0) or 0)
    neutral_rate = float(metrics.get("neutral_rate", 0.0) or 0.0)
    failed_claims = metrics.get("failed_claims", []) or []
    insufficient = sum(
        1 for item in failed_claims if item.get("failure_category") == "insufficient_evidence"
    )
    is_invalid = neutral_rate >= 0.8 or (total > 0 and insufficient >= max(5, total // 2))
    return {
        "is_valid_comparison": not is_invalid,
        "status": "invalid_search_collapsed" if is_invalid else "valid",
        "neutral_rate": round(neutral_rate, 3),
        "insufficient_evidence_failures": insufficient,
    }

def normalize_run_entry(batch_name, artifact_path: Path, stack_label):
    artifact_path = artifact_path.resolve() if not artifact_path.is_absolute() else artifact_path
    payload = load_json(artifact_path)
    metrics = payload.get("benchmark_metrics", {})
    validity = infer_run_validity(metrics, payload.get("run_validity", {}))
    failed_claims = metrics.get("failed_claims", []) or []
    return {
        "batch_name": batch_name,
        "artifact_path": str(artifact_path.relative_to(REPO_ROOT)),
        "stack_label": stack_label,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "run_validity": validity,
        "metrics": {
            "accuracy": metrics.get("accuracy"),
            "neutral_rate": metrics.get("neutral_rate"),
            "false_positive_rate": metrics.get("false_positive_rate"),
            "correct_predictions": metrics.get("correct_predictions"),
            "total_claims": metrics.get("total_claims"),
        },
        "failed_claims": failed_claims,
    }


def load_existing_ledger():
    if LEDGER_JSON.exists():
        return load_json(LEDGER_JSON)
    return {
        "policy": {
            "default_stack_label": "recommended_v9",
            "recurring_threshold": 2,
            "validity_field": "run_validity.is_valid_comparison",
            "phase2_reopen_threshold": 2,
            "phase3_reopen_threshold": 2,
        },
        "run_history": [],
        "active_residuals": [],
        "one_off_recent_failures": [],
        "phase_signals": {},
        "latest_cycle": {},
    }


def dedupe_run_history(run_history):
    latest_by_key = {}
    for row in run_history:
        key = (row.get("artifact_path"), row.get("batch_name"), row.get("stack_label"))
        latest_by_key[key] = row
    return list(latest_by_key.values())


def classify_primary_cause(failure_categories):
    mapped = Counter(
        FAILURE_TO_PRIMARY_CAUSE.get(category, "stance_only")
        for category in failure_categories
    )
    return mapped.most_common(1)[0][0] if mapped else "stance_only"


def recompute_residuals(ledger, cycle_entries):
    threshold = int(ledger["policy"]["recurring_threshold"])
    valid_runs = [
        run for run in ledger["run_history"]
        if run.get("run_validity", {}).get("is_valid_comparison") is True
    ]

    grouped = defaultdict(list)
    for run in valid_runs:
        for failure in run.get("failed_claims", []):
            key = (run.get("stack_label"), failure.get("claim"))
            grouped[key].append({
                "batch_name": run.get("batch_name"),
                "artifact_path": run.get("artifact_path"),
                "predicted_verdict": failure.get("predicted_verdict"),
                "expected_verdict": failure.get("expected_verdict"),
                "failure_category": failure.get("failure_category"),
            })

    active = []
    for (stack_label, claim), rows in grouped.items():
        if len(rows) < threshold:
            continue
        categories = [row.get("failure_category") for row in rows]
        active.append({
            "claim": claim,
            "stack_label": stack_label,
            "occurrences": len(rows),
            "batches": sorted({row.get("batch_name") for row in rows if row.get("batch_name")}),
            "latest_predicted_verdict": rows[-1].get("predicted_verdict"),
            "expected_verdict": rows[-1].get("expected_verdict"),
            "primary_cause": classify_primary_cause(categories),
            "failure_categories": dict(Counter(categories)),
        })

    active.sort(key=lambda row: (-row["occurrences"], row["claim"]))

    latest_valid_cycle_runs = [
        row for row in cycle_entries
        if row.get("run_validity", {}).get("is_valid_comparison") is True
    ]
    recurring_claims = {row["claim"] for row in active}
    one_off = []
    for run in latest_valid_cycle_runs:
        for failure in run.get("failed_claims", []):
            if failure.get("claim") in recurring_claims:
                continue
            one_off.append({
                "claim": failure.get("claim"),
                "batch_name": run.get("batch_name"),
                "predicted_verdict": failure.get("predicted_verdict"),
                "expected_verdict": failure.get("expected_verdict"),
                "primary_cause": FAILURE_TO_PRIMARY_CAUSE.get(
                    failure.get("failure_category"), "stance_only"
                ),
                "failure_category": failure.get("failure_category"),
            })

    phase2_count = sum(1 for row in active if row["primary_cause"] == "relevance_ranking")
    phase3_count = sum(
        1 for row in active if row["primary_cause"] == "aggregation_or_passage_collapse"
    )
    ledger["active_residuals"] = active
    ledger["one_off_recent_failures"] = one_off
    ledger["phase_signals"] = {
        "phase2": {
            "status": "reopen_watch" if phase2_count >= 2 else "stable",
            "recurring_claim_count": phase2_count,
        },
        "phase3": {
            "status": "reopen_watch" if phase3_count >= 2 else "stable",
            "recurring_claim_count": phase3_count,
        },
    }


def render_markdown(ledger):
    latest = ledger.get("latest_cycle", {})
    lines = [
        "# Residual Ledger",
        "",
        f"Status: monitoring ledger as of {latest.get('timestamp', datetime.now().date().isoformat())}",
        "",
        "This note tracks only valid benchmark runs on the current monitoring stack.",
        "Invalid search-collapsed runs are excluded from phase decisions.",
        "",
        "## Monitoring Policy",
        "",
        f"- default stack: `{ledger['policy']['default_stack_label']}`",
        f"- recurring threshold: `{ledger['policy']['recurring_threshold']}` valid runs on the same stack",
        "- canonical batches:",
        "  - `baseline_30claim`",
        "  - `multilingual_regression`",
        "  - `fresh_realtime`",
        "",
        "## Latest Cycle",
        "",
        f"- cycle label: `{latest.get('cycle_label', 'unknown')}`",
        f"- stack label: `{latest.get('stack_label', 'unknown')}`",
        "",
    ]

    for run in latest.get("runs", []):
        validity = run.get("run_validity", {})
        metrics = run.get("metrics", {})
        lines.extend([
            f"### {run.get('batch_name')}",
            "",
            f"- artifact: `{run.get('artifact_path')}`",
            f"- validity: `{validity.get('status')}`",
            f"- accuracy: `{metrics.get('accuracy')}`",
            f"- neutral rate: `{metrics.get('neutral_rate')}`",
            f"- false-positive rate: `{metrics.get('false_positive_rate')}`",
            "",
        ])

    lines.extend([
        "## Active Recurring Residuals",
        "",
    ])

    if ledger.get("active_residuals"):
        for row in ledger["active_residuals"]:
            lines.extend([
                f"### {row['claim']}",
                "",
                f"- stack: `{row['stack_label']}`",
                f"- occurrences: `{row['occurrences']}`",
                f"- batches: `{', '.join(row['batches'])}`",
                f"- primary cause: `{row['primary_cause']}`",
                f"- latest predicted verdict: `{row['latest_predicted_verdict']}`",
                "",
            ])
    else:
        lines.extend([
            "- No recurring residuals yet.",
            "",
        ])

    lines.extend([
        "## One-Off Failures From Latest Valid Cycle",
        "",
    ])

    if ledger.get("one_off_recent_failures"):
        for row in ledger["one_off_recent_failures"]:
            lines.append(
                f"- `{row['claim']}` ({row['batch_name']}): `{row['predicted_verdict']}` vs `{row['expected_verdict']}` -> `{row['primary_cause']}`"
            )
        lines.append("")
    else:
        lines.extend([
            "- None.",
            "",
        ])

    phase2 = ledger["phase_signals"]["phase2"]
    phase3 = ledger["phase_signals"]["phase3"]
    lines.extend([
        "## Phase Signals",
        "",
        f"- Phase 2: `{phase2['status']}` (`{phase2['recurring_claim_count']}` recurring relevance-ranked claims)",
        f"- Phase 3: `{phase3['status']}` (`{phase3['recurring_claim_count']}` recurring aggregation-collapse claims)",
        "",
        "## Current Decision",
        "",
        "- keep the current stack as-is",
        "- continue periodic evaluation",
        "- reopen Phase 2 or Phase 3 only if recurring valid residuals cross the stated thresholds",
        "",
    ])
    return "\n".join(lines)


def write_ledger(ledger):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    LEDGER_JSON.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    LEDGER_MD.write_text(render_markdown(ledger), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run or reuse the monitoring cycle and update the residual ledger.")
    parser.add_argument("--label", default=None, help="Optional label for the monitoring cycle.")
    parser.add_argument("--stack-label", default=None, help="Override stack label in stored metadata.")
    parser.add_argument("--skip-env-check", action="store_true", help="Skip recommended-stack env validation.")
    parser.add_argument("--reuse-baseline", default=None, help="Reuse an existing 30-claim artifact.")
    parser.add_argument("--reuse-multilingual", default=None, help="Reuse an existing multilingual artifact.")
    parser.add_argument("--reuse-fresh", default=None, help="Reuse an existing fresh realtime artifact.")
    args = parser.parse_args()

    stack_label = infer_stack_label(args.stack_label)
    if not args.skip_env_check:
        mismatches = check_env_matches_recommended()
        if mismatches:
            print("Recommended stack env mismatch detected:")
            for key, current, expected in mismatches:
                print(f"- {key}: current={current!r} expected={expected!r}")
            raise SystemExit("Aborting: current env does not match the recommended monitoring stack.")

    cycle_label = args.label or f"{now_stamp()}_{stack_label}"
    cycle_dir = LOGS_DIR / "monitoring_cycles" / cycle_label
    cycle_dir.mkdir(parents=True, exist_ok=True)

    artifact_paths = {}
    reuse_map = {
        "baseline_30claim": args.reuse_baseline,
        "multilingual_regression": args.reuse_multilingual,
        "fresh_realtime": args.reuse_fresh,
    }

    for batch_name in BATCHES:
        reuse_path = reuse_map[batch_name]
        if reuse_path:
            artifact_paths[batch_name] = Path(reuse_path)
            continue
        output_path = cycle_dir / BATCHES[batch_name]["filename"]
        run_benchmark(batch_name, output_path)
        artifact_paths[batch_name] = output_path

    cycle_entries = [
        normalize_run_entry(batch_name, artifact_paths[batch_name], stack_label)
        for batch_name in BATCHES
    ]

    cycle_summary = {
        "cycle_label": cycle_label,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stack_label": stack_label,
        "runs": cycle_entries,
    }
    (cycle_dir / "monitoring_cycle_summary.json").write_text(
        json.dumps(cycle_summary, indent=2),
        encoding="utf-8",
    )

    ledger = load_existing_ledger()
    ledger["run_history"] = dedupe_run_history(ledger["run_history"] + cycle_entries)
    ledger["latest_cycle"] = cycle_summary
    recompute_residuals(ledger, cycle_entries)
    write_ledger(ledger)

    print(f"Monitoring cycle saved to {cycle_dir}")
    print(f"Residual ledger updated at {LEDGER_MD}")


if __name__ == "__main__":
    main()



