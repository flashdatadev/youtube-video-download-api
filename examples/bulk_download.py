"""Submit a file of video IDs and export every delivery result as JSONL."""

import argparse
import json
from pathlib import Path

from flashdata_download import collect_bulk, submit_bulk

from ._shared import client_and_storage, positive_timeout, run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_ids", type=Path, help="UTF-8 file: one video ID per line, no header")
    parser.add_argument("--audio", action="store_true", help="Deliver MP3 instead of MP4")
    parser.add_argument("--output-dir", type=Path, default=Path("output/bulk"))
    parser.add_argument("--timeout", type=positive_timeout, default=3600)
    args = parser.parse_args()
    client, storage = client_and_storage()
    checkpoint = args.output_dir / "download.job.json"
    options = (
        {"download_type": "audio", "output_format": "mp3", "audio_quality": "192"}
        if args.audio
        else {"download_type": "audio_video", "output_format": "mp4", "video_quality": "<=720"}
    )
    with client:
        job_id = submit_bulk(
            client,
            args.video_ids,
            storage=storage,
            checkpoint=checkpoint,
            **options,
        )
        print(f"Accepted {job_id}; checkpoint: {checkpoint}", flush=True)
        summary = collect_bulk(
            client,
            checkpoint,
            output=args.output_dir / "downloads.jsonl",
            timeout=args.timeout,
        )
    print(json.dumps(summary, indent=2))
    counts = summary["counts"]
    if summary["failed_rows"] or counts.get("failed") or counts.get("invalid"):
        raise SystemExit(2)


if __name__ == "__main__":
    run(main)
