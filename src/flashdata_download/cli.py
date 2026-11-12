"""Offline demo command. Live requests are explicit Python examples."""

from __future__ import annotations

import argparse
from pathlib import Path

from .demo import run_demo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser(
        "demo", help="Write synthetic delivery examples without network access"
    )
    demo.add_argument("--output", type=Path, default=Path("output/demo"))
    args = parser.parse_args(argv)
    try:
        destination = run_demo(args.output)
    except OSError as exc:
        parser.exit(1, f"Could not create demo output: {exc}\n")
    print(f"Offline demo saved to {destination}")
    print("delivery.json: one illustrative MP4 delivery receipt")
    print("downloads.jsonl: one completed row and one failed row")
    print("Synthetic data only. No media downloaded, network requests or credits used.")
    return 0
