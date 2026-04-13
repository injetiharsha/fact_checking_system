import asyncio
import sys

import benchmark_indian_languages as base


def _ensure_arg(flag: str, value: str) -> None:
    if flag not in sys.argv:
        sys.argv.extend([flag, value])


_ensure_arg("--claims-file", "benchmark_claims/indian_languages_factual.json")
_ensure_arg("--output", "indian_language_factual_benchmark_results.json")


if __name__ == "__main__":
    asyncio.run(base.main())
