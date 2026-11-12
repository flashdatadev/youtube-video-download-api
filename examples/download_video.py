"""Download YouTube video with audio to cloud storage, then save its delivery JSON."""

import argparse
from pathlib import Path

from flashdata_download import collect_download, submit_download

from ._shared import client_and_storage, run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", help="YouTube video ID, watch URL, Shorts URL or youtu.be link")
    parser.add_argument("--quality", default="<=720", help="For example: <=720, ==1080 or best")
    parser.add_argument("--format", choices=["mp4", "webm", "mkv"], default="mp4")
    parser.add_argument("--metadata", action="store_true", help="Deliver companion metadata JSON")
    parser.add_argument("--output-dir", type=Path, default=Path("output/video"))
    args = parser.parse_args()
    client, storage = client_and_storage()
    checkpoint = args.output_dir / "download.job.json"
    with client:
        job_id = submit_download(
            client,
            args.video,
            storage=storage,
            checkpoint=checkpoint,
            download_type="audio_video",
            output_format=args.format,
            video_quality=args.quality,
            upload_metadata=args.metadata,
        )
        print(f"Accepted {job_id}; checkpoint: {checkpoint}", flush=True)
        result = collect_download(client, checkpoint, output=args.output_dir / "delivery.json")
    print("Delivered media:", result["results"][0]["file_url"])


if __name__ == "__main__":
    run(main)
