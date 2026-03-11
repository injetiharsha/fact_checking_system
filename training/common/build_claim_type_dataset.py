import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.utils import ensure_dir, read_json, stratified_split_records


SEED_RECORDS = [
    {"text": "The Earth revolves around the Sun.", "label": "factual", "source": "seed"},
    {"text": "Paris is the capital of France.", "label": "factual", "source": "seed"},
    {"text": "Jupiter is the largest planet in the solar system.", "label": "factual", "source": "seed"},
    {"text": "Water boils at 100 degrees Celsius at sea level.", "label": "factual", "source": "seed"},
    {"text": "Mars has two moons.", "label": "factual", "source": "seed"},
    {"text": "Saturn has rings.", "label": "factual", "source": "seed"},
    {"text": "Sharks are older than trees.", "label": "factual", "source": "seed"},
    {"text": "Bananas are berries.", "label": "factual", "source": "seed"},
    {"text": "The Roman Empire fell in 476 AD.", "label": "factual", "source": "seed"},
    {"text": "Lightning is hotter than the surface of the Sun.", "label": "factual", "source": "seed"},
    {"text": "Venus rotates in the opposite direction to most planets.", "label": "factual", "source": "seed"},
    {"text": "The Sun is a star.", "label": "factual", "source": "seed"},
    {"text": "Mercury is the closest planet to the Sun.", "label": "factual", "source": "seed"},
    {"text": "The Pacific Ocean is the largest ocean on Earth.", "label": "factual", "source": "seed"},
    {"text": "Bats are mammals.", "label": "factual", "source": "seed"},
    {"text": "An octopus has three hearts.", "label": "factual", "source": "seed"},
    {"text": "The Berlin Wall fell in 1989.", "label": "factual", "source": "seed"},
    {"text": "The United Nations was founded in 1945.", "label": "factual", "source": "seed"},
    {"text": "Greenland is the largest island in the world.", "label": "factual", "source": "seed"},
    {"text": "Lake Baikal is the deepest lake in the world.", "label": "factual", "source": "seed"},
    {"text": "The Sun rises in the east.", "label": "factual", "source": "seed"},
    {"text": "Sound travels faster in water than in air.", "label": "factual", "source": "seed"},
    {"text": "The moon landing was faked.", "label": "factual", "source": "seed"},
    {"text": "Climate change is a hoax.", "label": "factual", "source": "seed"},
    {"text": "Humans can breathe in space without equipment.", "label": "factual", "source": "seed"},
    {"text": "Trump is the best president ever.", "label": "opinion", "source": "seed"},
    {"text": "Chocolate is the best dessert.", "label": "opinion", "source": "seed"},
    {"text": "This movie is terrible.", "label": "opinion", "source": "seed"},
    {"text": "That policy is the worst economic decision in years.", "label": "opinion", "source": "seed"},
    {"text": "This phone has a great camera.", "label": "opinion", "source": "seed"},
    {"text": "The new logo looks awful.", "label": "opinion", "source": "seed"},
    {"text": "I believe remote work is better than office work.", "label": "opinion", "source": "seed"},
    {"text": "This restaurant should win an award.", "label": "opinion", "source": "seed"},
    {"text": "The film was boring and too long.", "label": "opinion", "source": "seed"},
    {"text": "This is the greatest sports team of all time.", "label": "opinion", "source": "seed"},
    {"text": "In my opinion, the redesign is a mistake.", "label": "opinion", "source": "seed"},
    {"text": "The coach made a brilliant decision.", "label": "opinion", "source": "seed"},
    {"text": "The user interface feels modern and elegant.", "label": "opinion", "source": "seed"},
    {"text": "This book is overrated.", "label": "opinion", "source": "seed"},
    {"text": "The soundtrack is beautiful.", "label": "opinion", "source": "seed"},
    {"text": "That speech was inspiring.", "label": "opinion", "source": "seed"},
    {"text": "The design looks outdated.", "label": "opinion", "source": "seed"},
    {"text": "The article is unfair and misleading.", "label": "opinion", "source": "seed"},
    {"text": "This policy is sensible.", "label": "opinion", "source": "seed"},
    {"text": "The match was exciting to watch.", "label": "opinion", "source": "seed"},
    {"text": "The presentation was confusing.", "label": "opinion", "source": "seed"},
    {"text": "The city has the best food in the country.", "label": "opinion", "source": "seed"},
    {"text": "The unemployment rate rose to 5.2%.", "label": "numerical", "source": "seed"},
    {"text": "India's population exceeded 1.4 billion in 2023.", "label": "numerical", "source": "seed"},
    {"text": "Scientists estimate 30,000 species go extinct annually.", "label": "numerical", "source": "seed"},
    {"text": "The company reported revenue of 12.5 million dollars.", "label": "numerical", "source": "seed"},
    {"text": "The city recorded 245 millimeters of rain in a day.", "label": "numerical", "source": "seed"},
    {"text": "Inflation fell to 3.1% in the latest report.", "label": "numerical", "source": "seed"},
    {"text": "The bridge is 2.3 kilometers long.", "label": "numerical", "source": "seed"},
    {"text": "The project cost 48 billion rupees.", "label": "numerical", "source": "seed"},
    {"text": "The study followed 1,250 participants for 6 months.", "label": "numerical", "source": "seed"},
    {"text": "The vaccine showed 92% efficacy in the trial.", "label": "numerical", "source": "seed"},
    {"text": "The earthquake measured 6.8 on the Richter scale.", "label": "numerical", "source": "seed"},
    {"text": "The school has 1,800 students and 95 teachers.", "label": "numerical", "source": "seed"},
    {"text": "World War II ended in 1945.", "label": "numerical", "source": "seed"},
    {"text": "The Roman Empire fell in 476 AD.", "label": "numerical", "source": "seed"},
    {"text": "The company hired 230 employees last year.", "label": "numerical", "source": "seed"},
    {"text": "The battery lasts 12 hours on a single charge.", "label": "numerical", "source": "seed"},
    {"text": "The building is 320 meters tall.", "label": "numerical", "source": "seed"},
    {"text": "The report said exports grew by 14% in Q2.", "label": "numerical", "source": "seed"},
    {"text": "The survey included 8,400 respondents.", "label": "numerical", "source": "seed"},
    {"text": "The medicine reduced symptoms in 68% of patients.", "label": "numerical", "source": "seed"},
    {"text": "The tunnel is 57 kilometers long.", "label": "numerical", "source": "seed"},
    {"text": "The startup raised 25 million dollars in funding.", "label": "numerical", "source": "seed"},
    {"text": "The best evidence suggests COVID kills 1-2% of cases.", "label": "mixed", "source": "seed"},
    {"text": "According to most experts, AI will be the most transformative technology.", "label": "mixed", "source": "seed"},
    {"text": "Many believe this policy will improve the economy by 10%.", "label": "mixed", "source": "seed"},
    {"text": "Experts say the treatment is promising, but results remain uncertain.", "label": "mixed", "source": "seed"},
    {"text": "Analysts expect inflation to ease, though the outlook is still fragile.", "label": "mixed", "source": "seed"},
    {"text": "Researchers estimate the risk is low, but more evidence is needed.", "label": "mixed", "source": "seed"},
    {"text": "Doctors think the patient will recover, although complications are possible.", "label": "mixed", "source": "seed"},
    {"text": "The data suggests growth may continue, but the forecast is uncertain.", "label": "mixed", "source": "seed"},
    {"text": "Most experts agree the reform could help, but costs may rise.", "label": "mixed", "source": "seed"},
    {"text": "Early reports indicate the storm is weakening, though conditions remain dangerous.", "label": "mixed", "source": "seed"},
    {"text": "Evidence points to a decline in cases, but underreporting is possible.", "label": "mixed", "source": "seed"},
    {"text": "According to analysts, demand may improve next quarter, but visibility is limited.", "label": "mixed", "source": "seed"},
    {"text": "Scientists think the treatment may help, but the data is still early.", "label": "mixed", "source": "seed"},
    {"text": "Most economists expect inflation to cool, although risks remain.", "label": "mixed", "source": "seed"},
    {"text": "Researchers believe the signal is real, but confirmation is pending.", "label": "mixed", "source": "seed"},
    {"text": "Observers say the reform could work, but costs might rise.", "label": "mixed", "source": "seed"},
    {"text": "The evidence indicates demand is weakening, though the trend may reverse.", "label": "mixed", "source": "seed"},
    {"text": "Experts agree the storm is weakening, but flooding remains a threat.", "label": "mixed", "source": "seed"},
    {"text": "Early studies suggest benefits, but larger trials are still needed.", "label": "mixed", "source": "seed"},
    {"text": "Analysts say the merger may succeed, though regulatory hurdles remain.", "label": "mixed", "source": "seed"},
    {"text": "Some data points to improvement, but the margin of error is high.", "label": "mixed", "source": "seed"},
    {"text": "According to doctors, recovery is likely, but complications are possible.", "label": "mixed", "source": "seed"},
]


def infer_label(text: str) -> tuple[str, float]:
    lowered = (text or "").strip().lower()
    if not lowered:
        return "mixed", 0.5

    opinion_markers = [
        r"\bbest\b",
        r"\bworst\b",
        r"\bterrible\b",
        r"\bgreat\b",
        r"\bshould\b",
        r"\bi think\b",
        r"\bi believe\b",
        r"\bin my opinion\b",
        r"\bawful\b",
        r"\bbrilliant\b",
        r"\bboring\b",
        r"\bgreatest\b",
    ]
    mixed_markers = [
        "according to most experts",
        "best evidence suggests",
        "experts believe",
        "many believe",
        "experts say",
        "analysts expect",
        "researchers estimate",
        "data suggests",
        "evidence points to",
        "according to analysts",
    ]
    numerical_patterns = [
        r"\d+\s*%",
        r"\d+\s*(million|billion|trillion)",
        r"\b\d{4}\b",
        r"\d+\s*(deaths?|cases?|people|species)",
    ]

    if any(re.search(pattern, lowered, re.IGNORECASE) for pattern in numerical_patterns):
        return "numerical", 0.8
    if any(marker in lowered for marker in mixed_markers):
        return "mixed", 0.75
    if any(re.search(pattern, lowered, re.IGNORECASE) for pattern in opinion_markers):
        return "opinion", 0.75
    return "factual", 0.85


def build_records(benchmark_path: Path) -> List[Dict]:
    benchmark = read_json(benchmark_path)
    records = []
    seen = set()
    next_id = 1

    for seed in SEED_RECORDS:
        text = str(seed["text"]).strip()
        seen.add(text.lower())
        records.append({
            "id": f"claim_type_{next_id}",
            "text": text,
            "label": seed["label"],
            "source": seed["source"],
            "confidence_hint": 0.95,
        })
        next_id += 1

    for row in benchmark.get("claims", []):
        text = str(row.get("claim", "")).strip()
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        label, confidence = infer_label(text)
        records.append({
            "id": f"claim_type_{next_id}",
            "text": text,
            "label": label,
            "source": "benchmark_claim",
            "confidence_hint": round(confidence, 3),
        })
        next_id += 1
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Build weakly labeled claim-type dataset.")
    parser.add_argument("--benchmark", default="parallel_test_results.json")
    parser.add_argument("--output-dir", default="data/claim_type/v1")
    args = parser.parse_args()

    records = build_records(Path(args.benchmark))
    output_dir = ensure_dir(args.output_dir)
    train_rows, val_rows, test_rows = stratified_split_records(
        records,
        label_key="label",
        validation_ratio=0.1,
        test_ratio=0.1,
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
        f"and {len(test_rows)} test claim-type examples to {output_dir}"
    )


if __name__ == "__main__":
    main()
