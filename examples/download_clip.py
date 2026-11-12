"""Download a time range from a YouTube video as an MP4 clip."""

import argparse
from pathlib import Path

from flashdata_download import collect_download, submit_download

from ._shared import client_and_storage, run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video")
    parser.add_argument("--start", default="00:00:10", help="HH:MM:SS")
    parser.add_argument("--end", default="00:00:40", help="HH:MM:SS, later than start")
    parser.add_argument("--output-dir", type=Path, default=Path("output/clip"))
    args = parser.parse_args()
    client, storage = client_and_storage()
    checkpoint = args.output_dir / "download.job.json"
    with client:
        job_id = submit_download(
            client,
            args.video,
            storage=storage,
            checkpoint=checkpoint,
            output_format="mp4",
            video_quality="<=720",
            start_at=args.start,
            end_at=args.end,
            upload_metadata=True,
        )
        print(f"Accepted {job_id}; checkpoint: {checkpoint}", flush=True)
        result = collect_download(client, checkpoint, output=args.output_dir / "delivery.json")
    print("Delivered clip:", result["results"][0]["file_url"])


if __name__ == "__main__":
    run(main)
