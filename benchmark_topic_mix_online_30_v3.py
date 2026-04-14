import asyncio
import sys


DEFAULT_CLAIMS_FILE = "benchmark_claims/topic_mix_online_30_v3.json"
DEFAULT_OUTPUT = "benchmark_topic_mix_online_30_v3_results.json"


def _inject_defaults():
    args = sys.argv[1:]
    if "--claims-file" not in args:
        args = ["--claims-file", DEFAULT_CLAIMS_FILE, *args]
    if "--output" not in args:
        args = [*args, "--output", DEFAULT_OUTPUT]
    sys.argv = [sys.argv[0], *args]


if __name__ == "__main__":
    _inject_defaults()
    from benchmark_topic_mix_30 import main

    asyncio.run(main())
