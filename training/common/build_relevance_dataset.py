import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evidence.relevance import RelevanceScorer
from evidence.router import EvidenceRouter
from training.common.utils import ensure_dir, read_json, stratified_split_records


MANUAL_RELEVANCE_SEEDS = [
    {
        "claim": "The printing press was invented by Johannes Gutenberg",
        "positive": "Goldsmith and inventor Johannes Gutenberg was the first European to introduce the printing press with movable type.",
        "negatives": [
            "A printing press is a mechanical device for applying pressure to an inked surface resting upon a print medium.",
            "The invention and global spread of the printing press was one of the most influential events in the second millennium.",
        ],
        "source": "manual_seed",
    },
    {
        "claim": "Octopuses have three hearts",
        "positive": "Octopuses have three hearts and blue blood.",
        "negatives": [
            "An octopus is a soft-bodied, eight-limbed mollusc of the order Octopoda.",
            "Octopuses are among the most intelligent and behaviourally diverse invertebrates.",
        ],
        "source": "manual_seed",
    },
    {
        "claim": "Sharks are older than trees",
        "positive": "Shark-like fish existed hundreds of millions of years before the first trees appeared on Earth.",
        "negatives": [
            "Sharks are a group of cartilaginous fishes characterized by five to seven gill slits on each side.",
            "Modern sharks are classified within the division Selachii.",
        ],
        "source": "manual_seed",
    },
    {
        "claim": "The United Nations was founded after World War II",
        "positive": "The United Nations was established in 1945 after the end of the Second World War.",
        "negatives": [
            "The United Nations is an intergovernmental organization focused on peace and security.",
            "The UN Charter sets out the purposes and principles of the organization.",
        ],
        "source": "manual_seed",
    },
    {
        "claim": "Humans can breathe in space without equipment",
        "positive": "Humans cannot survive in the vacuum of space without pressurized life-support equipment.",
        "negatives": [
            "Humans are the most widespread species of primate.",
            "Humans have large brains compared to body size.",
        ],
        "source": "manual_seed",
    },
    {
        "claim": "Bananas are berries",
        "positive": "A banana is botanically classified as a berry.",
        "negatives": [
            "Bananas are elongated edible fruits produced by large herbaceous plants.",
            "Most cultivated bananas are seedless.",
        ],
        "source": "manual_seed",
    },
    {
        "claim": "Climate change is a hoax",
        "positive": "A 2019 review of scientific papers found the consensus on the cause of climate change to be at 100%, and a 2021 study concluded that over 99% of scientific papers agree on the human cause of climate change.",
        "negatives": [
            "There are a number of myths surrounding climate change and its impacts.",
            "A few organizations with members in extractive industries hold non-committal positions, and some have tried to persuade the public that climate change is not happening.",
        ],
        "source": "manual_seed",
    },
    {
        "claim": "The moon landing was faked",
        "positive": "A Moon landing or lunar landing is the arrival of a spacecraft on the surface of the Moon, including both crewed and robotic missions.",
        "negatives": [
            "Moon landing conspiracy theories claim that some or all elements of the Apollo program landings were hoaxes.",
            "Conspiracy beliefs about the Moon landing became widespread after the missions.",
        ],
        "source": "manual_seed",
    },
    {
        "claim": "Mars has two moons",
        "positive": "Mars has two small, irregularly shaped moons, Phobos and Deimos.",
        "negatives": [
            "Mars is the fourth planet from the Sun.",
            "Mars is known as the Red Planet because of iron oxide on its surface.",
        ],
        "source": "manual_seed",
    },
    {
        "claim": "The Berlin Wall fell in 1989",
        "positive": "The Berlin Wall stood from 1961 to 1989 and fell as East Germany opened the border in November 1989.",
        "negatives": [
            "The Berlin Wall was a guarded concrete barrier that encircled West Berlin.",
            "Full demolition of the Wall continued into the early 1990s.",
        ],
        "source": "manual_seed",
    },
    {
        "claim": "The United Nations was founded after World War II",
        "positive": "The United Nations was established in 1945 after World War II.",
        "negatives": [
            "The history of the United Nations has its origins in World War II.",
            "The United Nations is an intergovernmental organization focused on peace and security.",
        ],
        "source": "manual_seed",
    },
    {
        "claim": "Humans can breathe in space without equipment",
        "positive": "Humans cannot survive or breathe in the vacuum of space without pressurized life-support equipment.",
        "negatives": [
            "A vacuum is space devoid of matter.",
            "Physicists use the term vacuum to describe a region with very low pressure.",
        ],
        "source": "manual_seed",
    },
]


def split_sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"[.!?]\s+", text or "")
        if sentence and sentence.strip()
    ]


def valid_sentence(sentence: str) -> bool:
    words = sentence.split()
    return 6 <= len(words) <= 80


def lexical_overlap(claim: str, sentence: str) -> float:
    claim_tokens = {
        token for token in re.findall(r"[a-z0-9]+", (claim or "").lower())
        if len(token) > 2
    }
    sentence_tokens = set(re.findall(r"[a-z0-9]+", (sentence or "").lower()))
    if not claim_tokens:
        return 0.0
    return len(claim_tokens & sentence_tokens) / len(claim_tokens)


def relation_signal(claim: str, sentence: str) -> float:
    claim_text = (claim or "").lower()
    sent_text = (sentence or "").lower()
    bonus = 0.0
    if re.search(r"\b(invented by|founded by|discovered by)\b", claim_text):
        if any(token in sent_text for token in ("invented", "introduced", "founded", "discovered")):
            bonus += 0.25
        if " by " in sent_text:
            bonus += 0.1
    if re.search(r"\b(older than|younger than|before|after)\b", claim_text):
        if any(token in sent_text for token in ("before", "after", "older", "younger", "first", "earliest", "later")):
            bonus += 0.2
    if re.search(r"\b(has|have)\b", claim_text):
        if any(token in sent_text for token in ("has", "have", "contains", "possess", "possesses")):
            bonus += 0.15
    if re.search(r"\b(\d{1,4}|one|two|three|four|five|six|seven|eight|nine|ten)\b", claim_text):
        if re.search(r"\b(\d{1,4}|one|two|three|four|five|six|seven|eight|nine|ten)\b", sent_text):
            bonus += 0.1
    return bonus


def add_manual_seed_records(records: List[Dict], next_id: int) -> int:
    for seed in MANUAL_RELEVANCE_SEEDS:
        records.append(
            {
                "id": f"relevance_{next_id}",
                "claim": seed["claim"],
                "candidate_sentence": seed["positive"],
                "label": 1,
                "source": seed["source"],
                "selection_origin": "manual_positive_seed",
            }
        )
        next_id += 1
        for negative in seed["negatives"]:
            records.append(
                {
                    "id": f"relevance_{next_id}",
                    "claim": seed["claim"],
                    "candidate_sentence": negative,
                    "label": 0,
                    "source": seed["source"],
                    "selection_origin": "manual_negative_seed",
                }
            )
            next_id += 1
    return next_id


async def build_records_from_claims(
    claims: List[str],
    max_claims: int = 30,
    max_sources_per_claim: int = 4,
    negatives_per_positive: int = 4,
    min_positive_overlap: float = 0.2,
) -> List[Dict]:
    router = EvidenceRouter()
    scorer = RelevanceScorer()
    records: list[Dict] = []
    next_id = 1

    next_id = add_manual_seed_records(records, next_id)

    for claim_idx, claim in enumerate(claims[:max_claims], start=1):
        print(f"Building relevance examples for claim {claim_idx}/{min(len(claims), max_claims)}: {claim}")
        try:
            evidence_list = await router.get_evidence(claim)
        except Exception as exc:
            print(f"Relevance dataset retrieval failed for '{claim}': {exc}")
            continue

        ranked_sources = sorted(
            evidence_list,
            key=lambda item: float(item.get("weight", 0.0)),
            reverse=True,
        )[:max_sources_per_claim]

        for ev in ranked_sources:
            text = str(ev.get("text", "")).strip()
            if not text:
                continue

            sentences = [sentence for sentence in split_sentences(text) if valid_sentence(sentence)]
            if len(sentences) < 2:
                continue

            scored = []
            for sentence in sentences:
                semantic = scorer.semantic_score(claim, sentence)
                overlap = lexical_overlap(claim, sentence)
                relation = relation_signal(claim, sentence)
                score = (semantic * 0.75) + (overlap * 0.2) + relation
                scored.append(
                    {
                        "sentence": sentence,
                        "score": score,
                        "semantic": semantic,
                        "overlap": overlap,
                        "relation": relation,
                    }
                )

            scored.sort(key=lambda item: item["score"], reverse=True)
            positive = scored[0]
            if positive["score"] < 0.22 or positive["overlap"] < min_positive_overlap:
                continue

            records.append(
                {
                    "id": f"relevance_{next_id}",
                    "claim": claim,
                    "candidate_sentence": positive["sentence"],
                    "label": 1,
                    "source": ev.get("source", "unknown"),
                    "selection_origin": "top_sentence_from_source",
                }
            )
            next_id += 1

            hard_negatives = [
                item for item in scored[1:]
                if (
                    item["semantic"] >= max(0.3, positive["semantic"] - 0.18)
                    or item["relation"] > 0
                    or item["overlap"] >= 0.18
                )
            ]
            easy_negatives = [
                item for item in scored[1:]
                if item not in hard_negatives and item["overlap"] <= 0.15
            ]

            chosen_negatives = hard_negatives[: max(1, negatives_per_positive // 2)]
            remaining = negatives_per_positive - len(chosen_negatives)
            if remaining > 0:
                chosen_negatives.extend(easy_negatives[:remaining])
            if len(chosen_negatives) < negatives_per_positive:
                fallback = [item for item in scored[1:] if item not in chosen_negatives]
                chosen_negatives.extend(fallback[: negatives_per_positive - len(chosen_negatives)])

            for negative in chosen_negatives[:negatives_per_positive]:
                records.append(
                    {
                        "id": f"relevance_{next_id}",
                        "claim": claim,
                        "candidate_sentence": negative["sentence"],
                        "label": 0,
                        "source": ev.get("source", "unknown"),
                        "selection_origin": "hard_negative_from_same_source"
                        if negative in hard_negatives
                        else "low_rank_sentence_from_same_source",
                    }
                )
                next_id += 1

    return records


async def main_async() -> None:
    parser = argparse.ArgumentParser(description="Build weakly labeled relevance dataset.")
    parser.add_argument("--benchmark", default="parallel_test_results.json")
    parser.add_argument("--output-dir", default="data/relevance/v4")
    parser.add_argument("--max-claims", type=int, default=30)
    parser.add_argument("--max-sources-per-claim", type=int, default=4)
    parser.add_argument("--negatives-per-positive", type=int, default=4)
    parser.add_argument("--min-positive-overlap", type=float, default=0.2)
    args = parser.parse_args()

    benchmark = read_json(Path(args.benchmark))
    claims = [str(row.get("claim", "")).strip() for row in benchmark.get("claims", []) if row.get("claim")]
    records = await build_records_from_claims(
        claims,
        max_claims=args.max_claims,
        max_sources_per_claim=args.max_sources_per_claim,
        negatives_per_positive=args.negatives_per_positive,
        min_positive_overlap=args.min_positive_overlap,
    )
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
        f"and {len(test_rows)} test relevance examples to {output_dir}"
    )


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
