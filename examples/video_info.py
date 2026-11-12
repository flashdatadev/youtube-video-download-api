"""Read a video's metadata and available formats before choosing download settings."""

import argparse
import json

from flashdata import FlashData

from flashdata_download import normalize_video_id

from ._shared import run, settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video")
    args = parser.parse_args()
    video_id = normalize_video_id(args.video)
    api_key, _ = settings()
    with FlashData(api_key=api_key) as client:
        result = client.youtube.metadata(video_id, include_formats=True, include_chapters=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run(main)
