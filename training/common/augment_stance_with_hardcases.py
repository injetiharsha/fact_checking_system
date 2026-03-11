import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.utils import ensure_dir, stratified_split_records


HARD_CASES = [
    {
        "claim": "The United Nations was founded after World War II",
        "evidence": "The United Nations was established in 1945 after the end of the Second World War.",
        "label": "SUPPORT",
    },
    {
        "claim": "The United Nations was founded after World War II",
        "evidence": "The United Nations Charter was signed on 26 June 1945 and came into force on 24 October 1945.",
        "label": "SUPPORT",
    },
    {
        "claim": "The United Nations was founded after World War II",
        "evidence": "The first steps toward the United Nations began in 1941, before the war had ended.",
        "label": "NEUTRAL",
    },
    {
        "claim": "Octopuses have three hearts",
        "evidence": "Octopuses have three hearts and blue blood.",
        "label": "SUPPORT",
    },
    {
        "claim": "Octopuses have three hearts",
        "evidence": "An octopus has a systemic heart and two branchial hearts.",
        "label": "SUPPORT",
    },
    {
        "claim": "Octopuses have three hearts",
        "evidence": "Octopuses are highly intelligent invertebrates with complex nervous systems.",
        "label": "NEUTRAL",
    },
    {
        "claim": "Climate change is a hoax",
        "evidence": "Climate change denial rejects the scientific consensus that human-caused global warming is real.",
        "label": "REFUTE",
    },
    {
        "claim": "Climate change is a hoax",
        "evidence": "There is overwhelming scientific evidence that climate change is occurring.",
        "label": "REFUTE",
    },
    {
        "claim": "Climate change is a hoax",
        "evidence": "Some politicians have described climate change as a hoax.",
        "label": "NEUTRAL",
    },
    {
        "claim": "Humans can breathe in space without equipment",
        "evidence": "A human exposed to the vacuum of space without a suit would quickly lose consciousness from lack of oxygen.",
        "label": "REFUTE",
    },
    {
        "claim": "Humans can breathe in space without equipment",
        "evidence": "Humans cannot survive in space without pressurized life-support equipment.",
        "label": "REFUTE",
    },
    {
        "claim": "Humans can breathe in space without equipment",
        "evidence": "Astronauts rely on spacesuits and spacecraft life-support systems to breathe in space.",
        "label": "REFUTE",
    },
    {
        "claim": "The moon landing was faked",
        "evidence": "Moon-landing conspiracy theories claim the Apollo landings were faked, but the Apollo missions did occur.",
        "label": "REFUTE",
    },
    {
        "claim": "The moon landing was faked",
        "evidence": "The six crewed Apollo moon landings really happened between 1969 and 1972.",
        "label": "REFUTE",
    },
    {
        "claim": "The moon landing was faked",
        "evidence": "Conspiracy theorists argue that the Moon landings had to be faked.",
        "label": "SUPPORT",
    },
    {
        "claim": "The Amazon River is the longest river in the world",
        "evidence": "The Amazon is often described as the longest or second-longest river in the world, disputed with the Nile.",
        "label": "REFUTE",
    },
    {
        "claim": "The Amazon River is the longest river in the world",
        "evidence": "The Amazon is the largest river by discharge, while its length compared with the Nile is disputed.",
        "label": "REFUTE",
    },
    {
        "claim": "Africa is the largest continent on Earth",
        "evidence": "Africa is the world's second-largest continent after Asia.",
        "label": "REFUTE",
    },
    {
        "claim": "Africa is the largest continent on Earth",
        "evidence": "Asia is the largest continent by land area.",
        "label": "REFUTE",
    },
    {
        "claim": "Bananas are berries",
        "evidence": "A banana is botanically a berry.",
        "label": "SUPPORT",
    },
    {
        "claim": "Bananas are berries",
        "evidence": "Bananas are elongated edible fruits produced by herbaceous plants.",
        "label": "NEUTRAL",
    },
    {
        "claim": "The printing press was invented by Johannes Gutenberg",
        "evidence": "Johannes Gutenberg introduced the movable-type printing press in Europe around 1440.",
        "label": "SUPPORT",
    },
    {
        "claim": "The printing press was invented by Johannes Gutenberg",
        "evidence": "The printing press transformed the spread of texts in Europe.",
        "label": "NEUTRAL",
    },
    {
        "claim": "Sharks are older than trees",
        "evidence": "Sharks existed hundreds of millions of years before the first trees evolved.",
        "label": "SUPPORT",
    },
    {
        "claim": "Sharks are older than trees",
        "evidence": "Modern sharks are a group of cartilaginous fishes.",
        "label": "NEUTRAL",
    },
    {
        "claim": "The Great Wall of China is visible from space",
        "evidence": "The Great Wall is generally not visible from low Earth orbit with the naked eye.",
        "label": "REFUTE",
    },
    {
        "claim": "The Great Wall of China is visible from space",
        "evidence": "Astronauts have said the Great Wall is difficult or impossible to see with the unaided eye from orbit.",
        "label": "REFUTE",
    },
    {
        "claim": "5G networks spread coronavirus",
        "evidence": "There is no evidence that 5G networks spread COVID-19.",
        "label": "REFUTE",
    },
    {
        "claim": "5G networks spread coronavirus",
        "evidence": "The 5G and COVID-19 theory is a conspiracy theory with no scientific basis.",
        "label": "REFUTE",
    },
    {
        "claim": "Drinking bleach cures COVID-19",
        "evidence": "Drinking bleach is dangerous and does not cure COVID-19.",
        "label": "REFUTE",
    },
    {
        "claim": "Drinking bleach cures COVID-19",
        "evidence": "Health agencies warn that ingesting bleach can cause serious harm.",
        "label": "REFUTE",
    },
]


def read_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Augment stance dataset with curated hard cases.")
    parser.add_argument("--input-dataset", default="data/stance/v2/dataset.jsonl")
    parser.add_argument("--output-dir", default="data/stance/v3")
    args = parser.parse_args()

    base_rows = read_jsonl(Path(args.input_dataset))
    extra_rows = []
    next_id = len(base_rows) + 1
    for row in HARD_CASES:
        extra_rows.append(
            {
                "id": f"stance_hard_{next_id}",
                "claim": row["claim"],
                "evidence": row["evidence"],
                "label": row["label"],
                "source": "local:hardcase_seed",
                "source_weight": 1.0,
                "weak_label": False,
            }
        )
        next_id += 1

    merged = base_rows + extra_rows
    train_rows, validation_rows, test_rows = stratified_split_records(
        merged,
        label_key="label",
        validation_ratio=0.1,
        test_ratio=0.1,
        seed=42,
    )

    output_dir = ensure_dir(args.output_dir)
    write_jsonl(output_dir / "train.jsonl", train_rows)
    write_jsonl(output_dir / "validation.jsonl", validation_rows)
    write_jsonl(output_dir / "test.jsonl", test_rows)
    write_jsonl(output_dir / "dataset.jsonl", merged)

    print(
        f"Wrote stance v3 dataset to {output_dir} "
        f"(base={len(base_rows)}, hardcases={len(extra_rows)}, total={len(merged)})"
    )


if __name__ == "__main__":
    main()
