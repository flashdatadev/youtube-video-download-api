"""A synthetic offline walkthrough; it never starts a download or contacts an API."""

from __future__ import annotations

import json
from pathlib import Path


def run_demo(output: str | Path) -> Path:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    result = {
        "demo": True,
        "id": "job_offline_demo",
        "source": "youtube_download",
        "status": "completed",
        "results": [
            {
                "file_url": "https://media.example.com/datasets/demo-video.mp4",
                "file_size": 12000000,
                "downloaded_bytes": 12000000,
                "output_format": "mp4",
                "duration": 30,
                "resolution": "1280x720",
                "md5": "00000000000000000000000000000000",
            }
        ],
    }
    (output / "delivery.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    rows = [
        {"demo": True, "video_id": "DEMO0000001", "status": "completed", "result": result},
        {
            "demo": True,
            "video_id": "DEMO0000002",
            "status": "failed",
            "error": {
                "code": "VIDEO_UNAVAILABLE",
                "message": "Synthetic unavailable-video example",
            },
        },
    ]
    (output / "downloads.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    (output / "README.txt").write_text(
        "Offline demo: synthetic delivery JSON and bulk rows.\n"
        "No media was downloaded. No network requests or credits were used.\n"
        "The example.com URL, video IDs and checksum are placeholders.\n",
        encoding="utf-8",
    )
    return output
