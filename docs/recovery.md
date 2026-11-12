# Job recovery and troubleshooting

## A polling timeout is not a failed download

The remote job continues when local waiting stops. Use the saved checkpoint and a
**new result output path**:

```bash
python -m examples.recover output/video/download.job.json --output output/recovered.json
python -m examples.recover output/bulk/download.job.json --bulk --output output/recovered.jsonl
```

These commands read the original job. They never create a new job, upload the ID file
again, or automatically resume paused work. They need your API key; storage credentials
are not resubmitted when collecting existing results.

## Checkpoint phases

| Phase | What happened | Next step |
| --- | --- | --- |
| `submitting`, no `job_id` | A checkpoint was reserved before the request | Reconcile the request before another submission; acceptance is unknown from this file alone |
| `submitted` | A single download ID was saved | Collect that ID |
| `created` | A bulk draft ID was saved, before upload | Inspect the draft and upload state |
| `uploaded` | Input upload returned; the start call may be in progress | Inspect server state before deciding whether to start the same draft |
| `started` | Bulk start returned | Collect that bulk ID |
| `completed` | Result export finished | Use the exported files; use a new output path if reading again |

The server's authenticated state is authoritative. A local phase can lag if the process
stopped between a remote response and a disk write.

### Bulk upload or start interrupted

Read `client.bulk.get(bulk_id)` with the official SDK. If it is `running`, `finalizing`
or `completed`, collect it. An `awaiting_upload` draft still needs a successful upload
and a start request. The signed upload descriptor is deliberately not persisted in a
checkpoint. If you no longer have a valid descriptor, inspect/cancel the unused draft
through your account or SDK before deliberately creating a replacement. Do not loop
over new bulk creation.

A lost start response is recoverable using the saved ID. Check whether the job is
already running before calling `client.bulk.start(bulk_id)` again.

### Paused bulk work

The SDK raises `JobPausedError`. Inspect the job's pause reason, resolve it, and explicitly
call `client.bulk.resume(bulk_id)` when appropriate. Recovery does not change credentials,
buy credits, resume or cancel jobs on your behalf.

### Partial exports and failed items

A completed bulk job can contain failed or invalid items. `collect_bulk` exports all
result rows and reports `failed_rows` plus the server's counts. The runnable bulk/recovery
examples return exit code `2` for partial failure after saving the rows.

If a result transfer stops partway through, the partial JSONL file stays on disk.
Collect the same job into a **fresh output filename** to obtain the full export.
Retrying failed media items is a separate, explicit submission.

## Common issues

| Symptom | Check |
| --- | --- |
| `401` / authentication failure | FlashData API key; a Google API key is different |
| Permission or download access denied | Key/account permissions and access to the download source |
| Storage upload `403` | Bucket, provider, region, endpoint and object-write permissions |
| Unavailable format | Inspect metadata; relax an exact resolution or advanced selector |
| Removed/private/unavailable source | Inspect the job error; repeated polling cannot restore the source |
| `file_url` cannot be opened anonymously | Read the object using your storage account or a signed link |
| Result not ready (`409`) | Continue polling the saved job ID |
| Result expired (`410`) | Check your bucket for delivered media before starting another download |
| `SubmissionUnknownError` | Preserve the checkpoint and reconcile acceptance before retrying |
| `FileExistsError` | Recover the existing run, or choose a new path for an intentional new task |

Download result JSON and bulk result parts have a 24-hour retention window after
completion. Export them promptly. Media stored in your own bucket follows your storage
retention settings.

## Checkpoint scope

Checkpoints prevent the same local checkpoint path from starting another request. They
are not a server-side idempotency key: another machine or a different filename can still
submit duplicate work. The SDK does not automatically retry network submissions.
