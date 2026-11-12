import json
import re
import subprocess
import sys
from pathlib import Path

import flashdata
import httpx
import pytest

from flashdata_download.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_offline_demo_outputs_are_explicitly_synthetic(tmp_path, capsys):
    output = tmp_path / "demo"
    assert main(["demo", "--output", str(output)]) == 0
    assert json.loads((output / "delivery.json").read_text())["demo"] is True
    assert all(
        json.loads(row)["demo"] for row in (output / "downloads.jsonl").read_text().splitlines()
    )
    assert "No media downloaded" in capsys.readouterr().out
    with pytest.raises(SystemExit) as exc:
        main(["demo", "--output", str(output)])
    assert exc.value.code == 1


@pytest.mark.parametrize(
    "name",
    [
        "download_video",
        "download_audio",
        "download_clip",
        "bulk_download",
        "recover",
        "video_info",
        "fetch_from_s3",
    ],
)
def test_every_recipe_has_credential_free_help(name):
    result = subprocess.run(
        [sys.executable, "-m", "examples." + name, "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout


def test_documentation_python_blocks_parse_and_local_links_exist():
    for path in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
        content = path.read_text(encoding="utf-8")
        for index, block in enumerate(re.findall(r"```python\n(.*?)```", content, re.DOTALL)):
            compile(block, f"{path}:{index}", "exec")
        for href in re.findall(r"\]\(([^)]+)\)", content):
            if not href.startswith(("https://", "http://", "#", "mailto:")):
                assert (path.parent / href.split("#")[0]).exists(), (path, href)


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf", "invalid"])
def test_bad_bulk_timeout_is_rejected_before_client_or_submission(monkeypatch, timeout):
    from examples import bulk_download

    def no_client():
        pytest.fail("Invalid arguments must not initialize a paid workflow")

    monkeypatch.setattr(bulk_download, "client_and_storage", no_client)
    monkeypatch.setattr(sys, "argv", ["bulk_download", "ids.txt", "--timeout", timeout])
    with pytest.raises(SystemExit) as exc:
        bulk_download.main()
    assert exc.value.code == 2


def test_readme_quickstart_runs_with_the_real_sdk(tmp_path, monkeypatch, capsys):
    content = (ROOT / "README.md").read_text(encoding="utf-8")
    example = re.findall(r"```python\n(.*?)```", content, re.DOTALL)[0]
    example = example.replace("YOUR_VIDEO_ID", "dQw4w9WgXcQ")
    real_client = flashdata.FlashData
    requests = []
    job_id = "job_readme0001"
    delivery = {
        "id": job_id,
        "source": "youtube_download",
        "status": "completed",
        "results": [{"file_url": "https://media.example/video.mp4", "file_size": 1024}],
    }

    def handler(request):
        requests.append(request)
        assert request.headers["x-api-key"] == "your-flashdata-api-key"
        if request.method == "POST":
            payload = json.loads(request.content)
            assert payload["video_id"] == "dQw4w9WgXcQ"
            assert payload["params"]["output_format"] == "mp4"
            assert payload["params"]["storage"]["storage_type"] == "s3"
            return httpx.Response(200, json={"id": job_id, "status": "pending"})
        if request.url.path.endswith("/results"):
            return httpx.Response(200, json=delivery)
        return httpx.Response(200, json={"job": {"id": job_id, "status": "completed"}})

    monkeypatch.setattr(
        flashdata,
        "FlashData",
        lambda **kwargs: real_client(**kwargs, transport=httpx.MockTransport(handler)),
    )
    monkeypatch.chdir(tmp_path)
    exec(compile(example, "README.md quickstart", "exec"), {})
    assert json.loads((tmp_path / "output/quickstart-delivery.json").read_text()) == delivery
    assert "1024 bytes" in capsys.readouterr().out
    assert [request.method for request in requests] == ["POST", "GET", "GET"]
