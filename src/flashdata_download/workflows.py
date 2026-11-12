"""Submission checkpoints and result exports; HTTP behavior stays in the SDK."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from flashdata import FlashData
from flashdata.errors import ProtocolError

from .validation import normalize_video_id, validate_id_file

_SOURCE = "youtube_download"


def _write_new(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as target:
        json.dump(data, target, ensure_ascii=False, indent=2)
        target.write("\n")
        target.flush()
        os.fsync(target.fileno())


def _replace(path: Path, data: dict[str, Any]) -> None:
    temporary = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as target:
            temporary = Path(target.name)
            json.dump(data, target, ensure_ascii=False, indent=2)
            target.write("\n")
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _reserve(path: Path, kind: str, **context: Any) -> dict[str, Any]:
    record = {"version": 1, "kind": kind, "source": _SOURCE, "phase": "submitting", **context}
    try:
        _write_new(path, record)
    except FileExistsError:
        raise FileExistsError(
            f"Checkpoint already exists: {path}. Recover its job instead of submitting again."
        ) from None
    return record


def _accept_id(path: Path, record: dict[str, Any], job_id: Any, phase: str) -> str:
    prefix = "bulk" if record["kind"] == "bulk" else "job"
    if not isinstance(job_id, str) or not re.fullmatch(rf"{prefix}_[A-Za-z0-9_-]+", job_id):
        raise ProtocolError("Submission returned no valid job ID. Reconcile it before retrying.")
    record.update(job_id=job_id, phase=phase)
    try:
        _replace(path, record)
    except OSError:
        raise OSError(
            f"Accepted job {job_id}, but its checkpoint could not be saved. Keep this ID."
        ) from None
    return job_id


def _read(path: Path, kind: str) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(record, dict) or (
        record.get("version"),
        record.get("kind"),
        record.get("source"),
    ) != (1, kind, _SOURCE):
        raise ValueError("This is not a compatible YouTube download checkpoint.")
    prefix = "bulk" if kind == "bulk" else "job"
    job_id = record.get("job_id")
    if not isinstance(job_id, str) or not re.fullmatch(rf"{prefix}_[A-Za-z0-9_-]+", job_id):
        raise ValueError("No accepted job ID was saved. Reconcile the submission before retrying.")
    return record


def _check_output(output: Path, checkpoint: Path) -> None:
    if output.resolve() == checkpoint.resolve():
        raise ValueError("Result output must be different from the checkpoint.")
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}. Choose a new output path.")
    output.parent.mkdir(parents=True, exist_ok=True)


def _check_source(job: dict[str, Any]) -> None:
    if job.get("source") not in {None, _SOURCE}:
        raise ProtocolError("The saved job is not a YouTube download job.")


def submit_download(
    client: FlashData,
    video: str,
    *,
    storage: dict[str, Any],
    checkpoint: str | Path,
    **options: Any,
) -> str:
    """Submit once and persist the accepted ID without storing any credentials."""
    video_id = normalize_video_id(video)
    path = Path(checkpoint)
    record = _reserve(path, "download", video_id=video_id)
    receipt = client.youtube.download(video_id, storage=storage, **options)
    return _accept_id(path, record, receipt.get("id"), "submitted")


def collect_download(
    client: FlashData,
    checkpoint: str | Path,
    *,
    output: str | Path,
    timeout: float = 600,
    poll_interval: float = 5,
) -> dict[str, Any]:
    """Wait and save delivery JSON for an existing job; never submit a new one."""
    checkpoint, output = Path(checkpoint), Path(output)
    record = _read(checkpoint, "download")
    _check_output(output, checkpoint)
    completed = client.jobs.wait(record["job_id"], timeout=timeout, poll_interval=poll_interval)
    _check_source(completed)
    result = client.jobs.result(record["job_id"])
    if not isinstance(result, dict):
        raise ProtocolError("Expected delivery result JSON.")
    if result.get("id") not in {None, record["job_id"]}:
        raise ProtocolError("The delivery result belongs to a different job.")
    _check_source(result)
    if result.get("status") not in {"done", "completed"} or not isinstance(
        result.get("results"), list
    ):
        raise ProtocolError("Expected completed delivery results.")
    if not result["results"] or any(
        not isinstance(item, dict)
        or not isinstance(item.get("file_url"), str)
        or not item["file_url"].strip()
        for item in result["results"]
    ):
        raise ProtocolError("The completed result does not contain media delivery locations.")
    _write_new(output, result)
    record.update(phase="completed", output=str(output.resolve()))
    _replace(checkpoint, record)
    return result


def submit_bulk(
    client: FlashData,
    video_ids: str | Path,
    *,
    storage: dict[str, Any],
    checkpoint: str | Path,
    **options: Any,
) -> str:
    """Create, upload and start one bulk job, saving its ID before upload."""
    video_ids, checkpoint = Path(video_ids), Path(checkpoint)
    count = validate_id_file(video_ids)
    record = _reserve(checkpoint, "bulk", input_file=str(video_ids.resolve()), input_count=count)
    receipt = client.bulk.create({"source": _SOURCE, "options": {**options, "storage": storage}})
    job_id = _accept_id(checkpoint, record, receipt.get("job", {}).get("id"), "created")
    client.bulk.upload_file(receipt, video_ids)
    record["phase"] = "uploaded"
    _replace(checkpoint, record)
    client.bulk.start(job_id)
    record["phase"] = "started"
    _replace(checkpoint, record)
    return job_id


def collect_bulk(
    client: FlashData,
    checkpoint: str | Path,
    *,
    output: str | Path,
    timeout: float = 3600,
    poll_interval: float = 5,
) -> dict[str, Any]:
    """Export all existing result rows, including failures, as JSONL."""
    checkpoint, output = Path(checkpoint), Path(output)
    record = _read(checkpoint, "bulk")
    _check_output(output, checkpoint)
    job = client.bulk.get(record["job_id"])
    _check_source(job)
    if job.get("status") == "awaiting_upload":
        raise ValueError(
            "This bulk draft has not started; see docs/recovery.md for upload recovery."
        )
    completed = client.bulk.wait(record["job_id"], timeout=timeout, poll_interval=poll_interval)
    _check_source(completed)
    rows = failed_rows = 0
    with output.open("x", encoding="utf-8") as target:
        for row in client.bulk.rows(record["job_id"]):
            target.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows += 1
            failed_rows += row.get("status") != "completed"
        target.flush()
        os.fsync(target.fileno())
    summary = {
        "job_id": record["job_id"],
        "rows": rows,
        "failed_rows": failed_rows,
        "counts": completed.get("counts", {}),
        "output": str(output.resolve()),
    }
    record.update(phase="completed", **summary)
    _replace(checkpoint, record)
    return summary
