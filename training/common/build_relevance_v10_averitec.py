import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.build_relevance_v9_residual import build_records as build_v9_records
from training.common.utils import ensure_dir, stratified_split_records


SUPPORTED_LABELS = {"supported", "refuted"}
MAX_ANSWER_CHARS = 320
MIN_ANSWER_WORDS = 5
MAX_ANSWER_WORDS = 80


def _clean_text(text: str) -> str:
    text = " ".join((text or "").split())
    return text.strip()


def _answer_is_usable(answer_text: str, answer_type: str | None) -> bool:
    text = _clean_text(answer_text)
    if not text:
        return False
    if (answer_type or "").strip().lower() == "unanswerable":
        return False
    words = text.split()
    if len(words) < MIN_ANSWER_WORDS or len(words) > MAX_ANSWER_WORDS:
        return False
    if len(text) > MAX_ANSWER_CHARS:
        return False
    if text.endswith("?"):
        return False
    return True


def _iter_averitec_answers(rows: list[dict]) -> list[dict]:
    extracted = []
    for row_idx, row in enumerate(rows):
        claim = _clean_text(str(row.get("claim") or ""))
        label = str(row.get("label") or "").strip().lower()
        if not claim or label not in SUPPORTED_LABELS:
            continue

        questions = row.get("questions") or []
        if not isinstance(questions, list):
            continue

        for question_block in questions:
            if not isinstance(question_block, dict):
                continue
            question_text = _clean_text(str(question_block.get("question") or ""))
            answers = question_block.get("answers") or []
            if not isinstance(answers, list):
                continue

            for answer in answers:
                if not isinstance(answer, dict):
                    continue
                answer_text = str(answer.get("answer") or "")
                answer_type = answer.get("answer_type")
                if not _answer_is_usable(answer_text, answer_type):
                    continue
                cleaned_answer = _clean_text(answer_text)
                source_url = _clean_text(str(answer.get("source_url") or ""))
                if not source_url:
                    continue
                extracted.append(
                    {
                        "claim": claim,
                        "label": label,
                        "candidate_sentence": cleaned_answer,
                        "question": question_text,
                        "source_url": source_url,
                        "source": "averitec_public_web",
                        "selection_origin": "averitec_answer_positive",
                        "row_idx": row_idx,
                    }
                )
    return extracted


def _dedupe_public_answers(rows: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for row in rows:
        key = (row["claim"], row["candidate_sentence"], row["source_url"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _sample_negatives(pool: list[dict], target_claim: str, k: int, rng: random.Random) -> list[dict]:
    candidates = [row for row in pool if row["claim"] != target_claim]
    rng.shuffle(candidates)
    picked = []
    seen_text = set()
    for row in candidates:
        text = row["candidate_sentence"]
        if text in seen_text:
            continue
        seen_text.add(text)
        picked.append(
            {
                "claim": target_claim,
                "candidate_sentence": text,
                "label": 0,
                "source": "averitec_public_web",
                "source_url": row["source_url"],
                "selection_origin": "averitec_cross_claim_negative",
            }
        )
        if len(picked) >= k:
            break
    return picked


def load_averitec_rows(paths: list[str]) -> list[dict]:
    all_rows = []
    for path_str in paths:
        path = Path(path_str)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Expected JSON list in {path}")
        all_rows.extend(payload)
    return all_rows


def build_public_records(paths: list[str], negatives_per_positive: int, seed: int) -> list[dict]:
    raw_rows = load_averitec_rows(paths)
    positives = _dedupe_public_answers(_iter_averitec_answers(raw_rows))
    rng = random.Random(seed)

    records = []
    next_id = 1
    for pos in positives:
        records.append(
            {
                "id": f"relevance_averitec_v10_{next_id}",
                "claim": pos["claim"],
                "candidate_sentence": pos["candidate_sentence"],
                "label": 1,
                "source": pos["source"],
                "source_url": pos["source_url"],
                "selection_origin": pos["selection_origin"],
            }
        )
        next_id += 1

        negatives = _sample_negatives(
            positives,
            target_claim=pos["claim"],
            k=negatives_per_positive,
            rng=rng,
        )
        for neg in negatives:
            records.append(
                {
                    "id": f"relevance_averitec_v10_{next_id}",
                    **neg,
                }
            )
            next_id += 1
    return records


def build_records(averitec_paths: list[str], negatives_per_positive: int = 1, seed: int = 42) -> list[dict]:
    base_records = build_v9_records()
    public_records = build_public_records(averitec_paths, negatives_per_positive=negatives_per_positive, seed=seed)
    return list(base_records) + public_records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build blended relevance v10 dataset from v9 residual seeds plus official AVeriTeC JSON."
    )
    parser.add_argument(
        "--averitec-file",
        action="append",
        required=True,
        help="Path to an official AVeriTeC split JSON file. Repeat for multiple splits.",
    )
    parser.add_argument("--output-dir", default="data/relevance/v10")
    parser.add_argument("--negatives-per-positive", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    records = build_records(
        averitec_paths=args.averitec_file,
        negatives_per_positive=max(1, int(args.negatives_per_positive)),
        seed=int(args.seed),
    )
    output_dir = ensure_dir(args.output_dir)
    train_rows, val_rows, test_rows = stratified_split_records(
        records,
        label_key="label",
        validation_ratio=0.15,
        test_ratio=0.15,
    )

    for file_name, rows in (
        ("train.jsonl", train_rows),
        ("validation.jsonl", val_rows),
        ("test.jsonl", test_rows),
        ("dataset.jsonl", records),
    ):
        output_path = output_dir / file_name
        with output_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(
        f"Wrote {len(train_rows)} train, {len(val_rows)} validation, and {len(test_rows)} test records to {output_dir}"
    )


if __name__ == "__main__":
    main()
