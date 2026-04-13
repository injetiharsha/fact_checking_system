"""
Legacy entrypoint only. Context classification runs in-process via
ClaimContextClassifier; this script is kept so old tooling paths still resolve.
"""

import argparse
import json
import sys


def _obsolete_payload():
    return {
        "error": "obsolete",
        "message": "Use ClaimContextClassifier in-process; subprocess helper is not supported.",
    }


def main():
    parser = argparse.ArgumentParser(description="Obsolete context inference helper.")
    parser.add_argument("--checkpoint", default="")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--text", default=None)
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    obsolete = _obsolete_payload()

    if args.serve:
        print(json.dumps({"status": "ready"}), flush=True)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            print(json.dumps(obsolete), flush=True)
        return

    print(json.dumps(obsolete), flush=True)
    sys.exit(1)


if __name__ == "__main__":
    main()
