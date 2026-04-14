import asyncio
import sys


DEFAULT_CLAIMS_FILE = "benchmark_claims/realfact_30_v1.json"
DEFAULT_OUTPUT = "benchmark_realfact_30_results.json"


def _inject_defaults():
    args = sys.argv[1:]
    if "--claims-file" not in args:
        args = ["--claims-file", DEFAULT_CLAIMS_FILE, *args]
    if "--output" not in args:
        args = [*args, "--output", DEFAULT_OUTPUT]
    sys.argv = [sys.argv[0], *args]


if __name__ == "__main__":
    _inject_defaults()
    from benchmark_multi_test import main

    asyncio.run(main())
