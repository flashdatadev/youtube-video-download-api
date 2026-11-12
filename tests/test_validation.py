import pytest

from flashdata_download.validation import normalize_video_id, validate_id_file


@pytest.mark.parametrize(
    "value",
    [
        "dQw4w9WgXcQ",
        "  dQw4w9WgXcQ  ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
        "youtu.be/dQw4w9WgXcQ?si=example",
        "https://youtube.com/shorts/dQw4w9WgXcQ",
        "https://youtube.com/live/dQw4w9WgXcQ",
        "https://youtube.com/embed/dQw4w9WgXcQ",
    ],
)
def test_supported_video_inputs(value):
    assert normalize_video_id(value) == "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "short",
        "YOUR_VIDEO_ID",
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
        "https://youtube.com@evil.example/watch?v=dQw4w9WgXcQ",
        "https://user@youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com:8080/watch?v=dQw4w9WgXcQ",
        "ftp://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/playlist?list=example",
        "https://youtube.com/watch?v=dQw4w9WgXcQ&v=jNQXAC9IVRw",
        "https://youtu.be/dQw4w9WgXcQ/extra",
    ],
)
def test_rejects_ambiguous_or_unrelated_inputs(value):
    with pytest.raises(ValueError):
        normalize_video_id(value)


def test_bulk_file_accepts_bom_and_windows_newlines(tmp_path):
    path = tmp_path / "ids.txt"
    path.write_bytes(b"\xef\xbb\xbfdQw4w9WgXcQ\r\njNQXAC9IVRw\r\n")
    assert validate_id_file(path) == 2


@pytest.mark.parametrize(
    "contents", ["", "video_id\ndQw4w9WgXcQ", "dQw4w9WgXcQ\n\n", "https://youtu.be/dQw4w9WgXcQ"]
)
def test_bulk_file_rejects_headers_urls_and_blank_rows(tmp_path, contents):
    path = tmp_path / "ids.txt"
    path.write_text(contents)
    with pytest.raises(ValueError):
        validate_id_file(path)
