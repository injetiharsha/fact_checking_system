import argparse
import json
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.utils import ensure_dir, stratified_split_records


DOMAIN_SEEDS = {
    "science": [
        ("Lightning is hotter than the surface of the Sun.", "physics"),
        ("Water expands when it freezes.", "physics"),
        ("Sound travels faster in water than in air.", "physics"),
        ("Humans share about 50 percent of their DNA with bananas.", "biology"),
        ("Bananas are berries.", "biology"),
        ("Octopuses have three hearts.", "biology"),
        ("The Earth is not flat.", "earth_science"),
        ("The Amazon River is one of the largest river systems in the world.", "earth_science"),
    ],
    "health": [
        ("Drinking bleach cures COVID-19.", "toxicology", ["medical_safety", "misinformation_sensitive"]),
        ("COVID-19 has killed over 6 million people worldwide.", "public_health"),
        ("Vaccines reduce the risk of severe disease.", "disease_treatment"),
        ("Aspirin can reduce fever.", "medicine"),
        ("Smoking increases the risk of lung disease.", "public_health"),
        ("ORS helps prevent dehydration.", "medicine"),
        ("A balanced diet supports overall health.", "nutrition"),
        ("Antibiotics do not work against viral infections.", "disease_treatment"),
    ],
    "technology": [
        ("5G networks spread coronavirus.", "telecom", ["misinformation_sensitive"]),
        ("Artificial intelligence will transform software development.", "software_ai"),
        ("Encryption protects data in transit.", "cybersecurity"),
        ("Fiber broadband is generally faster than DSL.", "internet"),
        ("A smartphone uses both hardware and software.", "hardware"),
        ("Machine learning models can be trained on labeled data.", "software_ai"),
        ("Mobile towers support wireless communication.", "telecom"),
        ("Social media platforms recommend content algorithmically.", "social_media"),
    ],
    "history": [
        ("The Berlin Wall fell in 1989.", "historical_events"),
        ("The printing press was invented by Johannes Gutenberg.", "historical_events"),
        ("World War II ended in 1945.", "wars_conflicts"),
        ("The Roman Empire fell in 476 AD.", "historical_events"),
        ("The United Nations was founded after World War II.", "diplomacy_treaties"),
        ("The League of Nations existed before the United Nations.", "diplomacy_treaties"),
        ("The Apollo 11 mission landed humans on the Moon in 1969.", "historical_events"),
        ("The French Revolution began in 1789.", "historical_events"),
    ],
    "politics_government": [
        ("The external affairs minister will speak in the Lok Sabha.", "foreign_affairs"),
        ("Tamil Nadu government announced a new school policy.", "public_policy", ["regional_local_claim"], "tamil_nadu"),
        ("Parliament passed the bill after debate.", "legislation"),
        ("The chief minister launched a new welfare scheme.", "public_policy"),
        ("The election commission announced the polling date.", "elections", ["election_sensitive"]),
        ("Foreign ministers met to discuss border security.", "foreign_affairs"),
        ("The cabinet approved the new regulation.", "governance"),
        ("The opposition criticized the budget policy.", "political_statements"),
    ],
    "economics_business": [
        ("The unemployment rate rose to 5.2%.", "labor_inflation"),
        ("Inflation fell to 3.1% in the latest report.", "macroeconomics"),
        ("The company reported revenue growth this quarter.", "corporate_claims"),
        ("The stock market closed higher on Friday.", "markets"),
        ("Interest rates were left unchanged by the central bank.", "finance"),
        ("Exports increased during the financial year.", "trade"),
        ("GDP growth slowed in the last quarter.", "macroeconomics"),
        ("A merger can change market competition.", "corporate_claims"),
    ],
    "geography": [
        ("Africa is the largest continent on Earth.", "continents"),
        ("Lake Baikal is the deepest lake on Earth.", "rivers_lakes"),
        ("Paris is the capital of France.", "capitals_borders"),
        ("Greenland is the largest island in the world.", "countries"),
        ("The Nile is a major river in Africa.", "rivers_lakes"),
        ("Mount Everest is the tallest mountain above sea level.", "mountains"),
        ("Australia is both a country and a continent.", "continents"),
        ("The Sahara is a large desert region.", "climate_regions"),
    ],
    "space_astronomy": [
        ("Mars has two moons.", "moons"),
        ("The moon landing was faked.", "space_missions", ["misinformation_sensitive"]),
        ("The Sun is a star.", "stars"),
        ("Saturn has rings.", "planets"),
        ("Venus rotates in the opposite direction to most planets.", "planets"),
        ("Jupiter is the largest planet in the solar system.", "planets"),
        ("Neptune is the farthest planet from the Sun.", "planets"),
        ("NASA launched multiple lunar missions.", "space_missions"),
    ],
    "environment_climate": [
        ("Climate change is a hoax.", "climate_change", ["misinformation_sensitive"]),
        ("Carbon emissions contribute to global warming.", "climate_change"),
        ("Cyclones can cause severe coastal flooding.", "disasters_weather"),
        ("Air pollution affects public health.", "pollution"),
        ("Biodiversity loss threatens ecosystems.", "biodiversity"),
        ("Deforestation can increase ecological damage.", "ecological_impacts"),
        ("Renewable energy can reduce emissions.", "sustainability"),
        ("Heat waves are becoming more frequent in some regions.", "disasters_weather"),
    ],
    "society_culture": [
        ("The census reported population growth in the district.", "demographics"),
        ("School enrollment increased this year.", "education"),
        ("Tamil is one of the classical languages of India.", "language_identity"),
        ("Many communities celebrate local harvest festivals.", "customs_traditions"),
        ("Literacy rates vary across regions.", "education"),
        ("Migration can change urban demographics.", "demographics"),
        ("Traditional dress varies across Indian states.", "customs_traditions"),
        ("Language policy can shape cultural identity.", "language_identity"),
    ],
    "law_crime": [
        ("The Supreme Court struck down the order.", "courts"),
        ("The regulation requires company disclosures.", "regulation"),
        ("Police arrested the suspect after the complaint.", "criminal_cases"),
        ("The High Court heard the appeal.", "courts"),
        ("The law was challenged on constitutional grounds.", "constitutional_issues"),
        ("The accused was charged under criminal law.", "criminal_cases"),
        ("Data protection rules require compliance.", "rights_compliance"),
        ("The court stayed the government order.", "courts"),
    ],
    "sports": [
        ("The player broke the tournament record.", "records"),
        ("The team won the championship final.", "teams"),
        ("The athlete qualified for the Olympics.", "athletes"),
        ("The match ended in a draw.", "tournaments"),
        ("The referee applied the offside rule.", "rules"),
        ("The club signed a new striker.", "teams"),
        ("The batsman scored a century in the match.", "athletes"),
        ("The tournament begins next week.", "tournaments"),
    ],
    "entertainment": [
        ("The movie won three awards.", "film"),
        ("The television series released a new season.", "television"),
        ("The singer released a new album.", "music"),
        ("The actor starred in a blockbuster film.", "celebrity"),
        ("The game launched with online multiplayer.", "gaming"),
        ("The streaming platform renewed the show.", "streaming_media"),
        ("The composer won a music award.", "music"),
        ("The film premiered at an international festival.", "film"),
    ],
    "general_factual": [
        ("Mercury is the closest planet to the Sun.", "entity_property"),
        ("Water is made of hydrogen and oxygen.", "encyclopedic"),
        ("Gold is a metal.", "entity_property"),
        ("A triangle has three sides.", "encyclopedic"),
        ("Birds have feathers.", "entity_property"),
        ("The Pacific Ocean is the largest ocean on Earth.", "encyclopedic"),
        ("Bats are mammals.", "entity_property"),
        ("Trees produce oxygen through photosynthesis.", "encyclopedic"),
    ],
}


def expanded_records() -> List[dict]:
    records = []
    next_id = 1
    for label, seeds in DOMAIN_SEEDS.items():
        for seed in seeds:
            text = seed[0]
            subcategory = seed[1]
            risk_flags = seed[2] if len(seed) > 2 and isinstance(seed[2], list) else []
            state_focus = seed[3] if len(seed) > 3 else None
            row = {
                "id": f"context_{next_id}",
                "text": text,
                "label": label,
                "subcategory": subcategory,
                "risk_flags": risk_flags,
                "state_focus": state_focus,
                "source": "seed",
                "confidence_hint": 0.95,
            }
            records.append(row)
            next_id += 1
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Build seed context-classification dataset.")
    parser.add_argument("--output-dir", default="data/context/v1")
    args = parser.parse_args()

    records = expanded_records()
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
        f"Wrote {len(train_rows)} train, {len(val_rows)} validation, and {len(test_rows)} test context examples to {output_dir}"
    )


if __name__ == "__main__":
    main()
