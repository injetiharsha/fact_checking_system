import argparse
import json
from pathlib import Path

DEFAULT_MANIFEST = {
    "dataset_name": "relevance_v13_broad_manifest",
    "sources": [
        {
            "name": "relevance_v9_existing",
            "type": "local_dataset",
            "path": "data/relevance/v9/dataset.jsonl",
            "role": "base_general_relevance",
            "enabled": True,
        },
        {
            "name": "relevance_v12_source_residual",
            "type": "local_dataset",
            "path": "data/relevance/v12_source_residual/dataset.jsonl",
            "role": "source_selection_residual",
            "enabled": True,
        },
        {
            "name": "averitec_train",
            "type": "public_raw_local",
            "path": "data/public/averitec/train.json",
            "role": "broad_public_claim_evidence",
            "enabled": True,
        },
        {
            "name": "averitec_dev",
            "type": "public_raw_local",
            "path": "data/public/averitec/dev.json",
            "role": "broad_public_claim_evidence",
            "enabled": True,
        },
        {
            "name": "india_official_curated",
            "type": "curated_seed_placeholder",
            "path": "data/relevance/seeds/india_official_curated_v13.jsonl",
            "role": "india_government_entity_acronym",
            "enabled": False,
        },
        {
            "name": "authoritative_vs_derivative_curated",
            "type": "curated_seed_placeholder",
            "path": "data/relevance/seeds/source_quality_curated_v13.jsonl",
            "role": "authoritative_vs_derivative",
            "enabled": False,
        },
    ],
    "targets": {
        "min_new_records": 500,
        "preferred_new_records": 2000,
        "india_records": 100,
        "authoritative_vs_derivative_records": 100,
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Write relevance v13 broad manifest scaffold.")
    parser.add_argument(
        "--output",
        default="training/relevance/relevance_v13_broad_manifest.json",
        help="Output manifest path.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(DEFAULT_MANIFEST, handle, ensure_ascii=False, indent=2)
    print(f"Wrote manifest to {output_path}")


if __name__ == "__main__":
    main()
