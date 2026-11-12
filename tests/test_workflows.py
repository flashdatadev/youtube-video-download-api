import gzip
import json
from types import SimpleNamespace

import httpx
import pytest
from flashdata import FlashData
from flashdata.errors import (
    JobFailedError,
    PollingTimeoutError,
    ProtocolError,
    SubmissionUnknownError,
)

from flashdata_download import collect_bulk, collect_download, submit_bulk, submit_download

VIDEO = "dQw4w9WgXcQ"
JOB = "job_example0001"
BULK = "bulk_example0001"
STORAGE = {
    "storage_type": "s3",
    "storage_url": "test-bucket",
    "region": "us-east-1",
    "access_key": "test-storage-access",
    "secret_key": "test-storage-secret",
}
RESULT = {
    "id": JOB,
    "source": "youtube_download",
    "status": "completed",
    "results": [{"file_url": "https://media.example/video.mp4", "file_size": 1024}],
}


def checkpoint(path, kind="download", job_id=JOB):
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "kind": kind,
                "source": "youtube_download",
                "job_id": job_id,
            }
        )
    )


@pytest.mark.parametrize(
    "options",
    [
        {"output_format": "mp4", "video_quality": "<=720", "upload_metadata": True},
        {"download_type": "audio", "output_format": "mp3", "audio_quality": "192"},
        {"output_format": "mp4", "start_at": "00:00:10", "end_at": "00:00:40"},
        {"output_format": "webm", "video_quality": "==1080", "fps": "<=30"},
    ],
)
def test_real_sdk_submits_documented_options_and_saves_id(tmp_path, options):
    path = tmp_path / "video.job.json"
    calls = []

    def handler(request):
        calls.append(request)
        assert json.loads(path.read_text())["phase"] == "submitting"
        assert request.url == "https://data.flashdata.dev/v1/queries"
        assert request.headers["x-api-key"] == "test-api-key"
        payload = json.loads(request.content)
        assert payload["source"] == "youtube_download"
        assert payload["video_id"] == VIDEO
        assert payload["params"] == {"storage": STORAGE, **options}
        return httpx.Response(200, json={"id": JOB, "status": "pending"})

    with FlashData(api_key="test-api-key", transport=httpx.MockTransport(handler)) as client:
        assert (
            submit_download(
                client,
                f"https://youtu.be/{VIDEO}",
                storage=STORAGE,
                checkpoint=path,
                **options,
            )
            == JOB
        )
        with pytest.raises(FileExistsError):
            submit_download(client, VIDEO, storage=STORAGE, checkpoint=path, **options)
    saved = path.read_text()
    assert json.loads(saved)["job_id"] == JOB
    assert "test-api-key" not in saved
    assert "test-storage" not in saved
    assert len(calls) == 1


def test_invalid_url_never_creates_a_checkpoint_or_contacts_api(tmp_path):
    path = tmp_path / "state.json"
    with pytest.raises(ValueError):
        submit_download(None, "https://evil.example/video", storage=STORAGE, checkpoint=path)
    assert not path.exists()


def test_lost_submission_response_leaves_a_replay_barrier(tmp_path):
    path = tmp_path / "state.json"
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("lost response", request=request)

    with FlashData(api_key="test-key", transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SubmissionUnknownError):
            submit_download(client, VIDEO, storage=STORAGE, checkpoint=path)
        with pytest.raises(FileExistsError):
            submit_download(client, VIDEO, storage=STORAGE, checkpoint=path)
        with pytest.raises(ValueError, match="Reconcile"):
            collect_download(client, path, output=tmp_path / "delivery.json")
    assert len(calls) == 1


def test_collect_uses_signed_result_without_forwarding_api_key(tmp_path):
    path, output = tmp_path / "state.json", tmp_path / "delivery.json"
    checkpoint(path)
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == "GET"
        if request.url.host == "results.example":
            assert "x-api-key" not in request.headers
            return httpx.Response(200, json=RESULT)
        if request.url.path == "/v2/api-access":
            return httpx.Response(200, json={"result_origin": "https://results.example"})
        if request.url.path.endswith("/results"):
            return httpx.Response(
                302, headers={"location": "https://results.example/result?token=fake"}
            )
        return httpx.Response(
            200, json={"job": {"id": JOB, "source": "youtube_download", "status": "completed"}}
        )

    with FlashData(api_key="test-key", transport=httpx.MockTransport(handler)) as client:
        assert collect_download(client, path, output=output) == RESULT
    assert json.loads(output.read_text()) == RESULT
    assert json.loads(path.read_text())["phase"] == "completed"
    assert "token=fake" not in path.read_text()
    assert len(calls) == 4


def test_poll_timeout_keeps_saved_id_for_recovery(tmp_path):
    path = tmp_path / "state.json"
    checkpoint(path)

    def wait(job_id, **kwargs):
        raise PollingTimeoutError(job_id)

    client = SimpleNamespace(jobs=SimpleNamespace(wait=wait))
    with pytest.raises(PollingTimeoutError):
        collect_download(client, path, output=tmp_path / "delivery.json")
    assert json.loads(path.read_text())["job_id"] == JOB
    assert not (tmp_path / "delivery.json").exists()


def test_failed_job_does_not_produce_success_output(tmp_path):
    path = tmp_path / "state.json"
    checkpoint(path)
    with FlashData(
        api_key="test-key",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"job": {"id": JOB, "status": "failed"}})
        ),
    ) as client:
        with pytest.raises(JobFailedError):
            collect_download(client, path, output=tmp_path / "delivery.json")
    assert not (tmp_path / "delivery.json").exists()


@pytest.mark.parametrize(
    "result",
    [
        {"status": "pending", "results": []},
        {"status": "completed", "results": []},
        {"status": "completed", "results": [{"title": "wrong payload"}]},
        {"status": "completed", "results": [{"file_url": ""}]},
        {**RESULT, "id": "job_other0001"},
        {**RESULT, "source": "youtube_transcript"},
    ],
)
def test_rejects_incomplete_or_wrong_source_results(tmp_path, result):
    path = tmp_path / "state.json"
    checkpoint(path)
    client = SimpleNamespace(
        jobs=SimpleNamespace(
            wait=lambda *_args, **_kwargs: {"status": "completed"},
            result=lambda _: result,
        )
    )
    with pytest.raises(ProtocolError):
        collect_download(client, path, output=tmp_path / "delivery.json")


def test_existing_output_is_not_overwritten_or_polled(tmp_path):
    path, output = tmp_path / "state.json", tmp_path / "delivery.json"
    checkpoint(path)
    output.write_text("existing user data")
    with pytest.raises(FileExistsError):
        collect_download(None, path, output=output)
    assert output.read_text() == "existing user data"


def test_real_sdk_bulk_lifecycle_saves_id_before_upload_and_exports_failures(tmp_path):
    path = tmp_path / "bulk.job.json"
    ids = tmp_path / "ids.txt"
    ids.write_text(VIDEO + "\n")
    rows = [
        {"index": 0, "video_id": VIDEO, "status": "completed", "result": RESULT},
        {
            "index": 1,
            "video_id": "jNQXAC9IVRw",
            "status": "failed",
            "error": {"code": "UNAVAILABLE"},
        },
    ]
    receipt = {
        "job": {"id": BULK, "status": "awaiting_upload"},
        "upload": {
            "method": "PUT",
            "href": "https://results.example/input?secret=fake",
            "contentType": "text/plain; charset=utf-8",
        },
    }
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        if request.url.host == "results.example":
            assert "x-api-key" not in request.headers
            if request.method == "PUT":
                assert json.loads(path.read_text())["job_id"] == BULK
                assert request.content == ids.read_bytes()
                return httpx.Response(200)
            if request.url.path == "/part":
                return httpx.Response(
                    200,
                    content=gzip.compress("".join(json.dumps(row) + "\n" for row in rows).encode()),
                )
            return httpx.Response(200, json={"parts": [{"number": 0}]})
        if request.url.path == "/v2/api-access":
            return httpx.Response(200, json={"result_origin": "https://results.example"})
        if request.method == "POST" and request.url.path == "/v2/bulk-jobs":
            body = json.loads(request.content)
            assert body["options"]["storage"] == STORAGE
            return httpx.Response(201, json=receipt)
        if request.url.path.endswith("/start"):
            assert json.loads(path.read_text())["phase"] == "uploaded"
            return httpx.Response(200, json={"job": {"id": BULK, "status": "running"}})
        if "/results" in request.url.path:
            location = "/part" if request.url.path.endswith("/0") else "/manifest"
            return httpx.Response(302, headers={"location": "https://results.example" + location})
        return httpx.Response(
            200,
            json={
                "job": {
                    "id": BULK,
                    "status": "completed",
                    "source": "youtube_download",
                    "counts": {"completed": 1, "failed": 1, "invalid": 0},
                }
            },
        )

    with FlashData(api_key="test-key", transport=httpx.MockTransport(handler)) as client:
        assert submit_bulk(client, ids, storage=STORAGE, checkpoint=path) == BULK
        summary = collect_bulk(client, path, output=tmp_path / "downloads.jsonl")
    assert summary["rows"] == 2
    assert summary["failed_rows"] == 1
    assert [
        json.loads(line) for line in (tmp_path / "downloads.jsonl").read_text().splitlines()
    ] == rows
    assert "secret=fake" not in path.read_text()
    assert "test-storage" not in path.read_text()
    assert calls.count(("POST", "/v2/bulk-jobs")) == 1
    assert calls.count(("PUT", "/input")) == 1


def test_bulk_invalid_input_fails_before_create(tmp_path):
    path, ids = tmp_path / "state.json", tmp_path / "ids.txt"
    ids.write_text("invalid")
    with pytest.raises(ValueError):
        submit_bulk(None, ids, storage=STORAGE, checkpoint=path)
    assert not path.exists()


def test_unstarted_bulk_draft_is_not_implicitly_started(tmp_path):
    path = tmp_path / "state.json"
    checkpoint(path, "bulk", BULK)
    client = SimpleNamespace(bulk=SimpleNamespace(get=lambda _: {"status": "awaiting_upload"}))
    with pytest.raises(ValueError, match="has not started"):
        collect_bulk(client, path, output=tmp_path / "rows.jsonl")


def test_bulk_partial_export_can_be_recovered_to_new_file(tmp_path):
    path = tmp_path / "state.json"
    checkpoint(path, "bulk", BULK)

    def interrupted_rows(_):
        yield {"status": "completed", "video_id": VIDEO}
        raise OSError("interrupted read")

    bulk = SimpleNamespace(
        get=lambda _: {"status": "completed"},
        wait=lambda *_args, **_kwargs: {"status": "completed", "counts": {}},
        rows=interrupted_rows,
    )
    client = SimpleNamespace(bulk=bulk)
    with pytest.raises(OSError, match="interrupted"):
        collect_bulk(client, path, output=tmp_path / "partial.jsonl")
    assert len((tmp_path / "partial.jsonl").read_text().splitlines()) == 1
    bulk.rows = lambda _: iter([{"status": "completed", "video_id": VIDEO}])
    assert collect_bulk(client, path, output=tmp_path / "recovered.jsonl")["rows"] == 1


def test_checkpoint_cannot_be_used_as_output(tmp_path):
    path = tmp_path / "state.json"
    checkpoint(path)
    with pytest.raises(ValueError, match="different"):
        collect_download(None, path, output=path)
    assert json.loads(path.read_text())["job_id"] == JOB


def test_checkpoint_disk_failure_reports_accepted_id(tmp_path, monkeypatch):
    import flashdata_download.workflows as workflows

    def fail(*_args):
        raise OSError("disk full")

    monkeypatch.setattr(workflows, "_replace", fail)
    client = SimpleNamespace(youtube=SimpleNamespace(download=lambda *a, **kw: {"id": JOB}))
    with pytest.raises(OSError, match=JOB):
        submit_download(client, VIDEO, storage=STORAGE, checkpoint=tmp_path / "state.json")
