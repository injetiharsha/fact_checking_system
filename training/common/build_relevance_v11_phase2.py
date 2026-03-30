import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.build_relevance_v9_residual import build_records as build_v9_records
from training.common.utils import ensure_dir, stratified_split_records


AMAZON_AMBIGUOUS_SOURCE_URL = "https://smartwatermagazine.com/q-a/what-longest-river-world"


PHASE2_CLEAN_V11_SEEDS = [
    {
        "claim": "The Amazon River is the longest river in the world",
        "positive": "Most standard references identify the Nile River, not the Amazon River, as the longest river in the world.",
        "negatives": [
            "The Amazon River carries more water than any other river on Earth.",
            "The Amazon basin covers a vast part of northern South America.",
        ],
        "source": "phase2_clean_seed",
        "source_url": "https://blogs.loc.gov/maps/2018/10/extremities-of-the-earth-the-longest-river-part-1/",
    },
    {
        "claim": "The Amazon River is the longest river in the world",
        "positive": "The Amazon is usually described as the largest river by discharge, while the Nile is usually described as the longest.",
        "negatives": [
            "The Amazon flows eastward across South America to the Atlantic Ocean.",
            "River systems can be compared by length, volume, or basin size.",
        ],
        "source": "phase2_clean_seed",
        "source_url": "https://education.nationalgeographic.org/resource/amazon-river/",
    },
    {
        "claim": "The Amazon River is the longest river in the world",
        "positive": "The Nile remains the most commonly accepted answer to the question of which river is the longest.",
        "negatives": [
            "The Amazon supports one of the most biodiverse regions in the world.",
            "Hydrologists sometimes debate how river length should be measured.",
        ],
        "source": "phase2_clean_seed",
        "source_url": "https://blogs.loc.gov/maps/2018/10/extremities-of-the-earth-the-longest-river-part-1/",
    },
    {
        "claim": "The Amazon River is the longest river in the world",
        "positive": "Reference works usually separate the Amazon's size and discharge from the Nile's status as the longest river.",
        "negatives": [
            "The Amazon rainforest depends on the river system that crosses the continent.",
            "The Amazon has numerous tributaries and a huge drainage basin.",
        ],
        "source": "phase2_clean_seed",
        "source_url": "https://education.nationalgeographic.org/resource/amazon-river/",
    },
    {
        "claim": "The Amazon River is the longest river in the world",
        "positive": "The Amazon is enormous, but the longest-river title is still more commonly given to the Nile.",
        "negatives": [
            "The Amazon's water volume is unmatched among the world's rivers.",
            "Different publications sometimes emphasize different river superlatives.",
        ],
        "source": "phase2_clean_seed",
        "source_url": "https://blogs.loc.gov/maps/2018/10/extremities-of-the-earth-the-longest-river-part-1/",
    },
    {
        "claim": "Humans share about 50 percent of their DNA with bananas",
        "positive": "At a broad gene-comparison level, humans and bananas share roughly half of their genes.",
        "negatives": [
            "Bananas are tropical fruits produced by plants in the genus Musa.",
            "Humans and bananas diverged along very different branches of life.",
        ],
        "source": "phase2_clean_seed",
        "source_url": "https://www.pfizer.com/news/articles/how_genetically_related_are_we_to_bananas",
    },
    {
        "claim": "Humans share about 50 percent of their DNA with bananas",
        "positive": "The common banana comparison is a simplified way of saying humans share about half of their genes with bananas.",
        "negatives": [
            "Genetic similarity can be reported in more than one way.",
            "Bananas contain carbohydrates, fiber, and potassium.",
        ],
        "source": "phase2_clean_seed",
        "source_url": "https://www.pfizer.com/news/articles/how_genetically_related_are_we_to_bananas",
    },
    {
        "claim": "Humans share about 50 percent of their DNA with bananas",
        "positive": "Humans do not share half of every DNA letter with bananas, but broad gene comparisons often land near 50 percent.",
        "negatives": [
            "Bananas and humans both use DNA as genetic material.",
            "Similarity figures depend on which genes and comparisons are used.",
        ],
        "source": "phase2_clean_seed",
        "source_url": "https://www.pfizer.com/news/articles/how_genetically_related_are_we_to_bananas",
    },
    {
        "claim": "Humans share about 50 percent of their DNA with bananas",
        "positive": "Biologists use the banana example to show that many basic genes are shared across living things, including humans and bananas.",
        "negatives": [
            "Bananas are flowering plants rather than animals.",
            "DNA comparisons are not the same as saying two species are closely related.",
        ],
        "source": "phase2_clean_seed",
        "source_url": "https://www.pfizer.com/news/articles/how_genetically_related_are_we_to_bananas",
    },
    {
        "claim": "Humans share about 50 percent of their DNA with bananas",
        "positive": "Saying humans share about 50 percent of their DNA with bananas is shorthand for a broad shared-gene comparison, not exact sequence identity.",
        "negatives": [
            "Living organisms often share genes used for core cellular functions.",
            "Bananas belong to a very different biological lineage from humans.",
        ],
        "source": "phase2_clean_seed",
        "source_url": "https://www.pfizer.com/news/articles/how_genetically_related_are_we_to_bananas",
    },
]


def _seed_rows_from_specs(seed_specs: list[dict]) -> list[dict]:
    rows = []
    for seed in seed_specs:
        rows.append(
            {
                "claim": seed["claim"],
                "candidate_sentence": seed["positive"],
                "label": 1,
                "source": seed["source"],
                "source_url": seed.get("source_url"),
                "selection_origin": "internet_backed_positive_seed_v11",
            }
        )
        for negative in seed["negatives"]:
            rows.append(
                {
                    "claim": seed["claim"],
                    "candidate_sentence": negative,
                    "label": 0,
                    "source": seed["source"],
                    "source_url": seed.get("source_url"),
                    "selection_origin": "internet_backed_negative_seed_v11",
                }
            )
    return rows


def _normalize_and_dedupe(rows: list[dict]) -> list[dict]:
    deduped = []
    seen = set()
    next_id = 1
    for row in rows:
        key = (row["claim"], row["candidate_sentence"], int(row["label"]))
        if key in seen:
            continue
        seen.add(key)
        normalized = dict(row)
        normalized["id"] = f"relevance_phase2_v11_{next_id}"
        next_id += 1
        deduped.append(normalized)
    return deduped


def build_records() -> list[dict]:
    base_records = []
    for row in build_v9_records():
        if row["claim"] == "The Amazon River is the longest river in the world" and row.get("source_url") == AMAZON_AMBIGUOUS_SOURCE_URL:
            continue
        base_records.append(dict(row))

    expanded_records = base_records + _seed_rows_from_specs(PHASE2_CLEAN_V11_SEEDS)
    return _normalize_and_dedupe(expanded_records)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build cleaned Phase 2 relevance v11 dataset with larger Amazon and bananas coverage."
    )
    parser.add_argument("--output-dir", default="data/relevance/v11")
    args = parser.parse_args()

    records = build_records()
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
