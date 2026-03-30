import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.build_relevance_v9_residual import RESIDUAL_RELEVANCE_V9_SEEDS
from training.common.utils import ensure_dir, stratified_split_records


SOURCE_RESIDUAL_V12_SEEDS = [
    {
        "claim": "DNA is shaped like a double helix",
        "positive": "The shape of DNA is a double helix.",
        "negatives": [
            "A closer look at the chemical structure of DNA shows four main building blocks called nucleotides.",
            "DNA is found in the cells of living things and stores hereditary information.",
        ],
        "source": "phase7_source_residual_seed",
        "source_url": "https://askabiologist.asu.edu/dna-shape-and-structure",
    },
    {
        "claim": "Jupiter is the largest planet in the solar system",
        "positive": "Jupiter is the largest planet in our solar system.",
        "negatives": [
            "Jupiter has many moons and a faint ring system.",
            "NASA has studied Jupiter with multiple spacecraft missions.",
        ],
        "source": "phase7_source_residual_seed",
        "source_url": "https://science.nasa.gov/jupiter/jupiter-facts/",
    },
    {
        "claim": "Lake Baikal is the deepest lake on Earth",
        "positive": "Lake Baikal is the deepest lake in the world.",
        "negatives": [
            "Lake Baikal is in southern Siberia.",
            "It also contains a large share of the world's unfrozen freshwater.",
        ],
        "source": "phase7_source_residual_seed",
        "source_url": "https://www.britannica.com/place/Lake-Baikal",
    },
    {
        "claim": "The Pacific Ocean is the largest ocean on Earth.",
        "positive": "The Pacific Ocean is the largest and deepest ocean on Earth.",
        "negatives": [
            "The Pacific covers a vast area between Asia, Australia, and the Americas.",
            "Oceans shape climate and weather around the world.",
        ],
        "source": "phase7_source_residual_seed",
        "source_url": "https://www.noaa.gov/education/resource-collections/ocean-coasts/ocean",
    },
    {
        "claim": "The Indian Space Research Organisation is commonly known by the acronym ISRO.",
        "positive": "Indian Space Research Organisation (ISRO) is the space agency of India.",
        "negatives": [
            "The organisation is involved in science, engineering and technology to harvest the benefits of outer space for India.",
            "India has carried out multiple space missions and satellite launches.",
        ],
        "source": "phase7_source_residual_seed",
        "source_url": "https://www.isro.gov.in/profile.html",
    },
    {
        "claim": "The Election Commission of India is a private company.",
        "positive": "The Election Commission of India is an autonomous constitutional authority responsible for administering election processes in India.",
        "negatives": [
            "It supervises elections to Parliament, state legislatures, and the offices of President and Vice-President.",
            "India conducts elections at national and state levels.",
        ],
        "source": "phase7_source_residual_seed",
        "source_url": "https://eci.gov.in/",
    },
    {
        "claim": "Penguins can fly long distances over the ocean.",
        "positive": "Penguins are flightless birds.",
        "negatives": [
            "Penguins are excellent swimmers and divers.",
            "They live primarily in the Southern Hemisphere.",
        ],
        "source": "phase7_source_residual_seed",
        "source_url": "https://www.britannica.com/animal/penguin",
    },
    {
        "claim": "The Titanic completed its first voyage successfully.",
        "positive": "Titanic sank on her maiden voyage after striking an iceberg.",
        "negatives": [
            "RMS Titanic departed Southampton on her maiden voyage in April 1912.",
            "The ship was one of the largest passenger liners of its time.",
        ],
        "source": "phase7_source_residual_seed",
        "source_url": "https://www.britannica.com/topic/Titanic",
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
    seeds = _dedupe_seeds(list(RESIDUAL_RELEVANCE_V9_SEEDS) + list(SOURCE_RESIDUAL_V12_SEEDS))
    for seed in seeds:
        base = {
            "claim": seed["claim"],
            "source": seed["source"],
            "source_url": seed.get("source_url"),
        }
        records.append(
            {
                "id": f"relevance_source_v12_{next_id}",
                **base,
                "candidate_sentence": seed["positive"],
                "label": 1,
                "selection_origin": "source_residual_positive_v12",
            }
        )
        next_id += 1
        for negative in seed["negatives"]:
            records.append(
                {
                    "id": f"relevance_source_v12_{next_id}",
                    **base,
                    "candidate_sentence": negative,
                    "label": 0,
                    "selection_origin": "source_residual_negative_v12",
                }
            )
            next_id += 1
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Build relevance v12 source residual dataset.")
    parser.add_argument("--output-dir", default="data/relevance/v12_source_residual")
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

    metadata = {
        "dataset_name": "relevance_v12_source_residual",
        "record_count": len(records),
        "train_count": len(train_rows),
        "validation_count": len(val_rows),
        "test_count": len(test_rows),
        "source_breakdown": {
            "phase2_residual_seed": sum(1 for row in records if row["source"] == "phase2_residual_seed"),
            "phase7_source_residual_seed": sum(1 for row in records if row["source"] == "phase7_source_residual_seed"),
        },
    }
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)

    print(
        f"Wrote {len(train_rows)} train, {len(val_rows)} validation, and {len(test_rows)} test records to {output_dir}"
    )


if __name__ == "__main__":
    main()
