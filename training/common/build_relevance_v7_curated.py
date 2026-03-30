import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.build_relevance_v6_manual import MANUAL_RELEVANCE_V6_SEEDS
from training.common.utils import ensure_dir, stratified_split_records


INTERNET_RELEVANCE_V7_SEEDS = [
    {
        "claim": "Climate change is a hoax",
        "positive": "Scientific evidence continues to show that human activities have warmed Earth?s surface and oceans, so climate change is not a hoax.",
        "negatives": [
            "Scientists focus on evidence rather than opinions when discussing climate change.",
            "Multiple scientific organizations have published statements about climate change.",
        ],
        "source": "curated_official",
        "source_url": "https://science.nasa.gov/climate-change/scientific-consensus",
    },
    {
        "claim": "The moon landing was faked",
        "positive": "On July 20, 1969, Neil Armstrong and Buzz Aldrin became the first humans to set foot on the Moon, so the Moon landing was not faked.",
        "negatives": [
            "Apollo 11 returned safely to Earth after its lunar mission.",
            "Moon landings include both crewed and robotic missions.",
        ],
        "source": "curated_official",
        "source_url": "https://www.nasa.gov/image-article/240000-miles-moon/",
    },
    {
        "claim": "Mars has two moons",
        "positive": "Mars has two small moons, Phobos and Deimos.",
        "negatives": [
            "Mars is one of the most explored bodies in the solar system.",
            "Phobos is the larger of Mars? two moons.",
        ],
        "source": "curated_official",
        "source_url": "https://science.nasa.gov/mars/facts/",
    },
    {
        "claim": "The United Nations was founded after World War II",
        "positive": "The United Nations officially came into existence on 24 October 1945, after World War II.",
        "negatives": [
            "The UN Charter was signed in San Francisco in June 1945.",
            "The United Nations is a global organization with member states around the world.",
        ],
        "source": "curated_official",
        "source_url": "https://www.un.org/en/charter-united-nations/",
    },
    {
        "claim": "The Great Wall of China is visible from space",
        "positive": "The Great Wall is difficult or impossible to see from Earth orbit without high-powered lenses and is not visible from the Moon.",
        "negatives": [
            "The Great Wall of China and Inner Mongolia are featured in astronaut photography.",
            "Some radar images can detect segments of the Great Wall from space.",
        ],
        "source": "curated_official",
        "source_url": "https://www.nasa.gov/image-article/great-wall/",
    },
    {
        "claim": "Drinking bleach cures COVID-19",
        "positive": "Drinking bleach does not prevent or cure COVID-19 and is extremely dangerous.",
        "negatives": [
            "Bleach and disinfectants can be used carefully on surfaces.",
            "Cleaning products may kill the virus on surfaces but not inside the body.",
        ],
        "source": "curated_official",
        "source_url": "https://www.who.int/emergencies/diseases/novel-coronavirus-2019/advice-for-public/myth-busters",
    },
    {
        "claim": "5G networks spread coronavirus",
        "positive": "5G mobile networks do not spread COVID-19 because viruses cannot travel on radio or mobile networks.",
        "negatives": [
            "5G is the latest wireless mobile phone technology.",
            "WHO continues to study health questions related to radiofrequency exposure.",
        ],
        "source": "curated_official",
        "source_url": "https://extranet.who.int/kobe_centre/sites/default/files/20200422_EN_New_mythbusters_rev.pdf",
    },
    {
        "claim": "Sound travels faster in water than in air",
        "positive": "Sound moves much faster in water than in air.",
        "negatives": [
            "The distance sound travels in the ocean depends on temperature and pressure.",
            "Underwater sound can travel very long distances in the ocean.",
        ],
        "source": "curated_official",
        "source_url": "https://oceanservice.noaa.gov/facts/sound.html",
    },
    {
        "claim": "Water expands when it freezes",
        "positive": "Water expands when it freezes because ice is less dense than liquid water.",
        "negatives": [
            "Ice floats because it is less dense than water.",
            "Water density changes with temperature and dissolved material.",
        ],
        "source": "curated_official",
        "source_url": "https://www.usgs.gov/index.php/water-science-school/science/water-density",
    },
    {
        "claim": "Lightning is hotter than the surface of the Sun",
        "positive": "The air heated by lightning can reach about 50,000 degrees Fahrenheit, which is hotter than the surface of the Sun.",
        "negatives": [
            "Lightning is the movement of electrical charges through the atmosphere.",
            "Rapid heating and cooling around lightning helps create thunder.",
        ],
        "source": "curated_official",
        "source_url": "https://www.weather.gov/safety/lightning-temperature",
    },
    {
        "claim": "Jupiter is the largest planet in the solar system",
        "positive": "Jupiter is the largest planet in our solar system.",
        "negatives": [
            "Jupiter is the fifth planet from the Sun.",
            "Jupiter has a very short day compared with Earth.",
        ],
        "source": "curated_official",
        "source_url": "https://science.nasa.gov/jupiter/facts/",
    },
    {
        "claim": "Saturn has rings",
        "positive": "Saturn has a ring system made of billions of pieces of ice and rock.",
        "negatives": [
            "Saturn is the sixth planet from the Sun.",
            "Saturn has many moons and a thick atmosphere.",
        ],
        "source": "curated_official",
        "source_url": "https://science.nasa.gov/saturn/facts/",
    },
    {
        "claim": "The Sun is a star",
        "positive": "The Sun is a yellow dwarf star at the center of our solar system.",
        "negatives": [
            "The Sun provides the energy that makes life on Earth possible.",
            "The Sun is made mostly of hydrogen and helium.",
        ],
        "source": "curated_official",
        "source_url": "https://science.nasa.gov/sun/facts/",
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
    seeds = _dedupe_seeds(list(MANUAL_RELEVANCE_V6_SEEDS) + INTERNET_RELEVANCE_V7_SEEDS)
    for seed in seeds:
        base = {
            "claim": seed["claim"],
            "source": seed["source"],
            "source_url": seed.get("source_url"),
        }
        records.append(
            {
                "id": f"relevance_manual_v7_{next_id}",
                **base,
                "candidate_sentence": seed["positive"],
                "label": 1,
                "selection_origin": "internet_backed_positive_seed_v7" if seed.get("source_url") else "manual_positive_seed_v7",
            }
        )
        next_id += 1
        for negative in seed["negatives"]:
            records.append(
                {
                    "id": f"relevance_manual_v7_{next_id}",
                    **base,
                    "candidate_sentence": negative,
                    "label": 0,
                    "selection_origin": "internet_backed_negative_seed_v7" if seed.get("source_url") else "manual_negative_seed_v7",
                }
            )
            next_id += 1
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Build blended manual + internet-backed relevance v7 dataset.")
    parser.add_argument("--output-dir", default="data/relevance/v7")
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
