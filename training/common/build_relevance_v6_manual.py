import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.utils import ensure_dir, stratified_split_records


MANUAL_RELEVANCE_V6_SEEDS = [
    {
        "claim": "Climate change is a hoax",
        "positive": "Human-caused climate change is supported by an overwhelming scientific consensus and is not a hoax.",
        "negatives": [
            "Some groups have tried to cast doubt on the scientific consensus about climate change.",
            "Climate change is discussed through surveys, reports, and policy debates around the world.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "The moon landing was faked",
        "positive": "Apollo 11 successfully landed humans on the Moon in 1969, so the Moon landing was not faked.",
        "negatives": [
            "Conspiracy theories about the Moon landing became popular after the Apollo missions.",
            "A Moon landing is the arrival of a spacecraft on the lunar surface.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Mars has two moons",
        "positive": "Mars has two natural moons named Phobos and Deimos.",
        "negatives": [
            "Mars is the fourth planet from the Sun.",
            "Mars is known as the Red Planet because of iron oxide on its surface.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "The Berlin Wall fell in 1989",
        "positive": "The Berlin Wall fell on 9 November 1989 during the Peaceful Revolution.",
        "negatives": [
            "The Berlin Wall was built in 1961 around West Berlin.",
            "Demolition of remaining sections continued into the 1990s.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "The United Nations was founded after World War II",
        "positive": "The United Nations officially came into existence in October 1945 after World War II.",
        "negatives": [
            "The United Nations is an intergovernmental organization focused on peace and security.",
            "The League of Nations was an earlier international organization.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Humans can breathe in space without equipment",
        "positive": "Humans cannot breathe or survive in the vacuum of space without pressurized life-support equipment.",
        "negatives": [
            "A vacuum is a region with extremely low pressure.",
            "Space is often treated as a near-vacuum in physics.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Australia is both a country and a continent",
        "positive": "Australia is both a sovereign country and the smallest continent.",
        "negatives": [
            "Australia lies between the Indian and Pacific Oceans.",
            "The Commonwealth of Australia includes mainland Australia and Tasmania.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Africa is the largest continent on Earth",
        "positive": "Asia is the largest continent on Earth, not Africa.",
        "negatives": [
            "Africa is the second-largest continent by area.",
            "Africa contains 54 recognized sovereign states.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Lake Baikal is the deepest lake on Earth",
        "positive": "Lake Baikal is the deepest lake in the world.",
        "negatives": [
            "Lake Baikal is located in Siberia, Russia.",
            "Baikal is also one of the oldest lakes on Earth.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Sound travels faster in water than in air",
        "positive": "Sound travels much faster in water than it does in air.",
        "negatives": [
            "Sound is a vibration that travels through a medium.",
            "Air and water are both common media for sound waves.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Humans share about 50 percent of their DNA with bananas",
        "positive": "Humans share roughly half of their genetic material with bananas at a broad gene level.",
        "negatives": [
            "Humans and bananas are both eukaryotic organisms.",
            "Genetic comparisons depend on how shared genes are measured.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Lightning is hotter than the surface of the Sun",
        "positive": "A lightning bolt can be hotter than the surface of the Sun.",
        "negatives": [
            "Lightning is a large electrical discharge in the atmosphere.",
            "The Sun has a much hotter core than its visible surface.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Water expands when it freezes",
        "positive": "Water expands when it freezes because ice is less dense than liquid water.",
        "negatives": [
            "Water is composed of hydrogen and oxygen.",
            "Ice forms a crystalline structure at low temperatures.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Venus rotates in the opposite direction to most planets",
        "positive": "Venus rotates in retrograde, opposite to the direction of most planets.",
        "negatives": [
            "Venus is the second planet from the Sun.",
            "Venus has a dense atmosphere rich in carbon dioxide.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Jupiter is the largest planet in the solar system",
        "positive": "Jupiter is the largest planet in the Solar System.",
        "negatives": [
            "Jupiter is a gas giant composed mainly of hydrogen and helium.",
            "Jupiter has a Great Red Spot that is a giant storm.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Neptune is the farthest planet from the Sun",
        "positive": "Neptune is the farthest known planet from the Sun.",
        "negatives": [
            "Neptune is an ice giant with strong winds.",
            "Pluto is classified as a dwarf planet rather than a planet.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "The Sun is a star",
        "positive": "The Sun is a star at the center of the Solar System.",
        "negatives": [
            "The Sun is the primary source of energy for Earth.",
            "The Sun is composed mostly of hydrogen and helium.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Saturn has rings",
        "positive": "Saturn has a prominent ring system made mostly of ice and rock.",
        "negatives": [
            "Saturn is a gas giant and the sixth planet from the Sun.",
            "Several other giant planets also have ring systems.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "World War II ended in 1945",
        "positive": "World War II ended in 1945.",
        "negatives": [
            "World War II began in 1939.",
            "The war involved most of the world's countries.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "The printing press was invented by Johannes Gutenberg",
        "positive": "Johannes Gutenberg introduced the movable-type printing press in Europe.",
        "negatives": [
            "Printing transformed the spread of books and information.",
            "Earlier woodblock printing existed in East Asia.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Bats are the only mammals capable of true flight",
        "positive": "Bats are the only mammals capable of sustained true flight.",
        "negatives": [
            "Flying squirrels can glide between trees.",
            "Bats belong to the order Chiroptera.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Sharks are older than trees",
        "positive": "Sharks appeared hundreds of millions of years before the first trees evolved.",
        "negatives": [
            "Modern sharks are cartilaginous fishes.",
            "Trees became widespread much later in Earth's history.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "The Great Wall of China is visible from space",
        "positive": "The Great Wall is generally not visible to the naked eye from low Earth orbit.",
        "negatives": [
            "The Great Wall is a series of fortifications built across northern China.",
            "Many human-made structures are difficult to see from space without magnification.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "5G networks spread coronavirus",
        "positive": "Viruses do not spread through radio waves or mobile networks like 5G.",
        "negatives": [
            "5G is the fifth generation of mobile communications technology.",
            "Conspiracy theories linked 5G and coronavirus during the pandemic.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Drinking bleach cures COVID-19",
        "positive": "Drinking bleach is dangerous and does not cure COVID-19.",
        "negatives": [
            "Bleach is a chemical disinfectant intended for surfaces.",
            "COVID-19 is caused by the SARS-CoV-2 virus.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Bananas are berries",
        "positive": "A banana is botanically classified as a berry.",
        "negatives": [
            "Bananas are elongated edible fruits produced by large herbaceous plants.",
            "Most cultivated bananas are seedless.",
        ],
        "source": "manual_seed_verified",
    },
    {
        "claim": "Octopuses have three hearts",
        "positive": "Octopuses have three hearts: one systemic heart and two branchial hearts.",
        "negatives": [
            "Octopuses are intelligent cephalopods with eight arms.",
            "Octopuses have a closed circulatory system.",
        ],
        "source": "manual_seed_verified",
    },
]


def build_manual_records() -> list[dict]:
    records = []
    next_id = 1
    for seed in MANUAL_RELEVANCE_V6_SEEDS:
        records.append(
            {
                "id": f"relevance_manual_v6_{next_id}",
                "claim": seed["claim"],
                "candidate_sentence": seed["positive"],
                "label": 1,
                "source": seed["source"],
                "selection_origin": "manual_positive_seed_v6",
            }
        )
        next_id += 1
        for negative in seed["negatives"]:
            records.append(
                {
                    "id": f"relevance_manual_v6_{next_id}",
                    "claim": seed["claim"],
                    "candidate_sentence": negative,
                    "label": 0,
                    "source": seed["source"],
                    "selection_origin": "manual_negative_seed_v6",
                }
            )
            next_id += 1
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Build broader manual relevance v6 dataset.")
    parser.add_argument("--output-dir", default="data/relevance/v6")
    args = parser.parse_args()

    records = build_manual_records()
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
        f"Wrote {len(train_rows)} train, {len(val_rows)} validation, "
        f"and {len(test_rows)} test manual relevance examples to {output_dir}"
    )


if __name__ == "__main__":
    main()
