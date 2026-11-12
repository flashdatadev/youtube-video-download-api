"""Read an existing job from its checkpoint without submitting or uploading again."""

import argparse
import json
from pathlib import Path

from flashdata import FlashData

from flashdata_download import collect_bulk, collect_download

from ._shared import positive_timeout, run, settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--bulk", action="store_true")
    parser.add_argument(
        "--output", type=Path, required=True, help="A new result JSON or bulk JSONL file"
    )
    parser.add_argument("--timeout", type=positive_timeout, default=3600)
    args = parser.parse_args()
    api_key, _ = settings()
    with FlashData(api_key=api_key) as client:
        collect = collect_bulk if args.bulk else collect_download
        result = collect(client, args.checkpoint, output=args.output, timeout=args.timeout)
    print(json.dumps(result, indent=2))
    if args.bulk:
        counts = result["counts"]
        if result["failed_rows"] or counts.get("failed") or counts.get("invalid"):
            raise SystemExit(2)


if __name__ == "__main__":
    run(main)
