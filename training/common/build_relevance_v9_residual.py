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


RESIDUAL_RELEVANCE_V9_SEEDS = [
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
        "claim": "The Amazon River is the longest river in the world",
        "positive": "Today, the most common answer to which is the world's longest river is the Nile River in northeast Africa.",
        "negatives": [
            "The Amazon carries more water than any other river.",
            "The Amazon basin spans multiple South American countries.",
        ],
        "source": "phase2_residual_seed",
        "source_url": "https://blogs.loc.gov/maps/2018/10/extremities-of-the-earth-the-longest-river-part-1/",
    },
    {
        "claim": "The Amazon River is the longest river in the world",
        "positive": "Some studies argue that the Amazon may be longer than the Nile depending on how the measurement is made.",
        "negatives": [
            "The Amazon begins in the Andes and flows eastward across South America.",
            "Scientists continue to study river systems with different measurement methods.",
        ],
        "source": "phase2_residual_seed",
        "source_url": "https://smartwatermagazine.com/q-a/what-longest-river-world",
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
        "claim": "Lake Baikal is the deepest lake on Earth",
        "positive": "This title goes to 1,642m-deep Lake Baikal, which is located in southern Siberia.",
        "negatives": [
            "It is possible to see to a depth of 40 meters from the surface in some parts of the lake.",
            "The lake formed as the planet's crust slowly pulled apart in that area.",
        ],
        "source": "phase2_residual_seed",
        "source_url": "https://www.sciencefocus.com/planet-earth/what-is-the-deepest-lake-on-earth",
    },
    {
        "claim": "Lake Baikal is the deepest lake on Earth",
        "positive": "Baikal is also the deepest lake, plunging to more than 1,600 meters.",
        "negatives": [
            "The world's oldest lake lies in southeastern Siberia.",
            "The lake has existed for about 25 million years.",
        ],
        "source": "phase2_residual_seed",
        "source_url": "https://www.iflscience.com/earths-oldest-and-deepest-lake-hides-a-dark-secret-cannibalistic-fish-80972",
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
        "claim": "The Roman Empire fell in 476 AD",
        "positive": "The Western Roman Empire fell in 476.",
        "negatives": [
            "The Roman Empire began with the reign of Emperor Augustus.",
            "The Roman Empire was ruled by emperors and supported by the Senate.",
        ],
        "source": "phase2_residual_seed",
        "source_url": "https://www.rome.net/roman-empire",
    },
    {
        "claim": "The Roman Empire fell in 476 AD",
        "positive": "Many historians cite 476 as the year the Western Empire suffered its death blow.",
        "negatives": [
            "Historians cite multiple overlapping factors for Rome's fall.",
            "The article explains several reasons Rome declined over time.",
        ],
        "source": "phase2_residual_seed",
        "source_url": "https://www.history.com/articles/8-reasons-why-rome-fell",
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
        + list(RESIDUAL_RELEVANCE_V9_SEEDS)
    )
    for seed in seeds:
        base = {
            "claim": seed["claim"],
            "source": seed["source"],
            "source_url": seed.get("source_url"),
        }
        records.append(
            {
                "id": f"relevance_manual_v9_{next_id}",
                **base,
                "candidate_sentence": seed["positive"],
                "label": 1,
                "selection_origin": "internet_backed_positive_seed_v9" if seed.get("source_url") else "manual_positive_seed_v9",
            }
        )
        next_id += 1
        for negative in seed["negatives"]:
            records.append(
                {
                    "id": f"relevance_manual_v9_{next_id}",
                    **base,
                    "candidate_sentence": negative,
                    "label": 0,
                    "selection_origin": "internet_backed_negative_seed_v9" if seed.get("source_url") else "manual_negative_seed_v9",
                }
            )
            next_id += 1
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Build blended manual + internet-backed relevance v9 residual dataset.")
    parser.add_argument("--output-dir", default="data/relevance/v9")
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
