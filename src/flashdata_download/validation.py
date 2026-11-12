"""Normalize user input without contacting YouTube or FlashData."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")
_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}


def normalize_video_id(value: str) -> str:
    """Accept an 11-character ID or a watch, Shorts, live, embed or youtu.be URL."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Provide a YouTube video ID or URL.")
    value = value.strip()
    if _VIDEO_ID.fullmatch(value):
        return value
    if "://" not in value:
        value = "https://" + value
    try:
        url = urlsplit(value)
        host = url.hostname
        if url.scheme not in {"https", "http"} or url.username or url.password or url.port:
            raise ValueError
        parts = url.path.strip("/").split("/")
        candidate = ""
        if host in {"youtu.be", "www.youtu.be"} and len(parts) == 1:
            candidate = parts[0]
        elif host in _YOUTUBE_HOSTS:
            if url.path in {"/watch", "/watch/"}:
                ids = parse_qs(url.query, keep_blank_values=True).get("v", [])
                if len(ids) == 1:
                    candidate = ids[0]
            elif len(parts) == 2 and parts[0] in {"shorts", "live", "embed"}:
                candidate = parts[1]
        if _VIDEO_ID.fullmatch(candidate):
            return candidate
    except ValueError:
        pass
    raise ValueError("Expected an 11-character YouTube video ID or a supported YouTube video URL.")


def validate_id_file(path: str | Path) -> int:
    """Check a bulk ID file by streaming it; return its number of input rows."""
    path = Path(path)
    if not path.is_file() or not 1 <= path.stat().st_size <= 2 * 1024**3:
        raise ValueError("The bulk input must be a regular UTF-8 ID file between 1 byte and 2 GiB.")
    count = 0
    with path.open(encoding="utf-8-sig") as source:
        for count, line in enumerate(source, 1):
            if not _VIDEO_ID.fullmatch(line.strip()):
                raise ValueError(
                    f"Invalid video ID on line {count}; use one ID per line, no header."
                )
    if count == 0:
        raise ValueError("The bulk ID file is empty.")
    return count
