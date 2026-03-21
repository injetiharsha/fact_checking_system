import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.build_relevance_v7_curated import INTERNET_RELEVANCE_V7_SEEDS
from training.common.build_relevance_v6_manual import MANUAL_RELEVANCE_V6_SEEDS
from training.common.utils import ensure_dir, stratified_split_records


RESIDUAL_RELEVANCE_V8_SEEDS = [
    {
        "claim": "Climate change is a hoax",
        "positive": "Climate change is real and is primarily caused by human activities, so it is not a hoax.",
        "negatives": [
            "Climate change is discussed in policy debates around the world.",
            "Scientists study climate using observations, models, and historical records.",
        ],
        "source": "phase2_residual_seed",
        "source_url": "https://www.un.org/en/climatechange/science/mythbusters",
    },
    {
        "claim": "5G networks spread coronavirus",
        "positive": "5G networks do not spread COVID-19 because viruses cannot travel on radio waves or mobile networks.",
        "negatives": [
            "5G is a wireless communications technology used by mobile networks.",
            "Conspiracy theories linked 5G to coronavirus during the pandemic.",
        ],
        "source": "phase2_residual_seed",
        "source_url": "https://www.who.int/emergencies/diseases/novel-coronavirus-2019/advice-for-public/myth-busters",
    },
    {
        "claim": "The Amazon River is the longest river in the world",
        "positive": "The Nile is traditionally recognized as the longest river in the world, not the Amazon.",
        "negatives": [
            "The Amazon is one of the largest river systems on Earth.",
            "River length measurements can vary by methodology.",
        ],
        "source": "phase2_residual_seed",
        "source_url": "https://education.nationalgeographic.org/resource/amazon-river/",
    },
    {
        "claim": "Greenland is the largest island in the world",
        "positive": "Greenland is the largest island in the world.",
        "negatives": [
            "Greenland is an autonomous territory within the Kingdom of Denmark.",
            "Australia is classified as a continent rather than an island.",
        ],
        "source": "phase2_residual_seed",
        "source_url": "https://www.britannica.com/place/Greenland",
    },
    {
        "claim": "Lake Baikal is the deepest lake on Earth",
        "positive": "Lake Baikal is the deepest lake in the world.",
        "negatives": [
            "Lake Baikal is located in Siberia in Russia.",
            "Baikal also contains a large share of the world's unfrozen freshwater.",
        ],
        "source": "phase2_residual_seed",
        "source_url": "https://www.britannica.com/place/Lake-Baikal",
    },
    {
        "claim": "Humans share about 50 percent of their DNA with bananas",
        "positive": "Humans share about half of their genes with bananas at a broad gene-comparison level.",
        "negatives": [
            "Humans and bananas are both living organisms with DNA.",
            "Genetic similarity depends on how genes and sequences are compared.",
        ],
        "source": "phase2_residual_seed",
        "source_url": "https://www.pfizer.com/news/articles/how_genetically_related_are_we_to_bananas",
    },
    {
        "claim": "The Roman Empire fell in 476 AD",
        "positive": "The Western Roman Empire is commonly dated to have fallen in 476 AD.",
        "negatives": [
            "The Roman Empire endured for centuries across Europe, North Africa, and the Near East.",
            "The Eastern Roman Empire continued after the fall of the Western Empire.",
        ],
        "source": "phase2_residual_seed",
        "source_url": "https://www.britannica.com/place/ancient-Rome",
    },
    {
        "claim": "Humans can breathe in space without equipment",
        "positive": "Humans cannot breathe or survive in the vacuum of space without a pressurized spacesuit or life-support equipment.",
        "negatives": [
            "Outer space is a near-vacuum with extremely low pressure.",
            "Spacesuits are designed to provide pressure, oxygen, and temperature control.",
        ],
        "source": "phase2_residual_seed",
        "source_url": "https://www.nasa.gov/humans-in-space/spacesuits/",
    },
]


def _dedupe_seeds(seeds: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for seed in seeds:
        key = (seed["claim"], seed["positive"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(seed)
    return deduped


def build_records() -> list[dict]:
    records = []
    next_id = 1
    seeds = _dedupe_seeds(
        list(MANUAL_RELEVANCE_V6_SEEDS)
        + list(INTERNET_RELEVANCE_V7_SEEDS)
        + list(RESIDUAL_RELEVANCE_V8_SEEDS)
    )
    for seed in seeds:
        base = {
            "claim": seed["claim"],
            "source": seed["source"],
            "source_url": seed.get("source_url"),
        }
        records.append(
            {
                "id": f"relevance_manual_v8_{next_id}",
                **base,
                "candidate_sentence": seed["positive"],
                "label": 1,
                "selection_origin": "internet_backed_positive_seed_v8" if seed.get("source_url") else "manual_positive_seed_v8",
            }
        )
        next_id += 1
        for negative in seed["negatives"]:
            records.append(
                {
                    "id": f"relevance_manual_v8_{next_id}",
                    **base,
                    "candidate_sentence": negative,
                    "label": 0,
                    "selection_origin": "internet_backed_negative_seed_v8" if seed.get("source_url") else "manual_negative_seed_v8",
                }
            )
            next_id += 1
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Build blended manual + internet-backed relevance v8 residual dataset.")
    parser.add_argument("--output-dir", default="data/relevance/v8")
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
