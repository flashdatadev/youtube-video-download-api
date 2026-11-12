"""Download YouTube audio as MP3, M4A or Opus into your cloud bucket."""

import argparse
from pathlib import Path

from flashdata_download import collect_download, submit_download

from ._shared import client_and_storage, run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video")
    parser.add_argument("--format", choices=["mp3", "m4a", "opus"], default="mp3")
    parser.add_argument("--quality", choices=["best", "320", "256", "192", "128"], default="192")
    parser.add_argument("--output-dir", type=Path, default=Path("output/audio"))
    args = parser.parse_args()
    client, storage = client_and_storage()
    checkpoint = args.output_dir / "download.job.json"
    with client:
        job_id = submit_download(
            client,
            args.video,
            storage=storage,
            checkpoint=checkpoint,
            download_type="audio",
            output_format=args.format,
            audio_quality=args.quality,
        )
        print(f"Accepted {job_id}; checkpoint: {checkpoint}", flush=True)
        result = collect_download(client, checkpoint, output=args.output_dir / "delivery.json")
    print("Delivered audio:", result["results"][0]["file_url"])


if __name__ == "__main__":
    run(main)
