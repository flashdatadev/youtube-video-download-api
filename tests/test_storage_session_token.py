import json
import sys
from types import SimpleNamespace

import httpx
import pytest
from flashdata import FlashData

from examples import fetch_from_s3
from flashdata_download import submit_download


@pytest.mark.parametrize("provider", ["s3", "s3_compatible", "oss", "cos", "bos", "tos"])
def test_real_sdk_forwards_temporary_storage_without_saving_secrets(tmp_path, provider):
    storage = {
        "storage_type": provider,
        "storage_url": "test-bucket",
        "access_key": "fixture-access",
        "secret_key": "fixture-secret",
        "session_token": "fixture-session-token",
    }
    storage.update(
        {
            "s3": {"region": "us-east-1"},
            "s3_compatible": {"endpoint_url": "https://storage.example.com"},
            "oss": {"endpoint_url": "https://oss-cn-hangzhou.aliyuncs.com"},
            "cos": {"storage_url": "test-bucket-1250000000", "region": "ap-guangzhou"},
            "bos": {"region": "bj"},
            "tos": {"region": "cn-beijing"},
        }[provider]
    )
    requests = []

    def handler(request):
        requests.append(request)
        assert json.loads(request.content)["params"]["storage"] == storage
        return httpx.Response(200, json={"id": "job_sts0001", "status": "pending"})

    checkpoint = tmp_path / "download.job.json"
    with FlashData(api_key="test-api-key", transport=httpx.MockTransport(handler)) as client:
        assert (
            submit_download(client, "dQw4w9WgXcQ", storage=storage, checkpoint=checkpoint)
            == "job_sts0001"
        )
    assert len(requests) == 1
    assert "fixture-" not in checkpoint.read_text()


@pytest.mark.parametrize("provider", ["s3", "s3_compatible"])
@pytest.mark.parametrize("token", [None, "fixture-session-token"])
def test_fetch_from_s3_forwards_optional_session_token(monkeypatch, tmp_path, provider, token):
    storage = {
        "storage_type": provider,
        "storage_url": "test-bucket",
        "access_key": "fixture-access",
        "secret_key": "fixture-secret",
        "endpoint_url": "https://storage.example.com",
        "region": "us-east-1",
    }
    if token is not None:
        storage["session_token"] = token
    calls = []

    def download(bucket, key, target):
        assert (bucket, key) == ("test-bucket", "media/video.mp4")
        target.write(b"synthetic-media")

    def client(service, **kwargs):
        assert service == "s3"
        calls.append(kwargs)
        return SimpleNamespace(download_fileobj=download)

    output = tmp_path / "video.mp4"
    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=client))
    monkeypatch.setattr(fetch_from_s3, "settings", lambda: ("unused", storage))
    monkeypatch.setattr(sys, "argv", ["fetch_from_s3", "media/video.mp4", "--output", str(output)])
    fetch_from_s3.main()
    assert calls == [
        {
            "aws_access_key_id": "fixture-access",
            "aws_secret_access_key": "fixture-secret",
            "aws_session_token": token,
            "endpoint_url": storage["endpoint_url"],
            "region_name": storage["region"],
        }
    ]
    assert output.read_bytes() == b"synthetic-media"
