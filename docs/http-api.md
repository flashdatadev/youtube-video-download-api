# YouTube download API requests and responses

The runnable toolkit uses the official Python SDK. These are the corresponding HTTP
shapes for integrating the same workflow into another Python application.

## Submit a single download

`POST https://data.flashdata.dev/v1/queries`

Headers: `X-API-Key: your-flashdata-api-key`, `Content-Type: application/json`.

```json
{
  "source": "youtube_download",
  "video_id": "YOUR_VIDEO_ID",
  "params": {
    "download_type": "audio_video",
    "video_quality": "<=720",
    "output_format": "mp4",
    "storage": {
      "storage_type": "s3",
      "storage_url": "your-media-bucket",
      "region": "us-east-1",
      "access_key": "your-storage-access-key",
      "secret_key": "your-storage-secret-key"
    }
  }
}
```

An accepted submission returns an ID and `status: pending`. Save the ID before doing
more work. It confirms acceptance, not completion.

## Poll and retrieve

1. `GET https://api.flashdata.dev/v2/jobs/JOB_ID`
2. Read `job.status` until `completed` or `failed`.
3. On completion, fetch `GET https://api.flashdata.dev/v2/jobs/JOB_ID/results`.

Authenticate API calls with the same key. Result retrieval can redirect to signed object
storage; use the SDK's result reader, which does not forward the key to that destination.
Some status responses also include `job.result` inline.

Illustrative completed result, shortened to useful delivery fields:

```json
{
  "id": "job_example0001",
  "source": "youtube_download",
  "status": "completed",
  "results": [{
    "file_url": "https://your-bucket.example.com/youtube/video.mp4",
    "file_size": 12000000,
    "downloaded_bytes": 12000000,
    "output_format": "mp4",
    "duration": 30,
    "resolution": "1280x720",
    "md5": "00000000000000000000000000000000"
  }]
}
```

The media URL belongs to your cloud destination. The result is JSON, not the video's
binary content. These example values and checksum are placeholders.

## Batch downloads

Use `client.queries.batch(queries)` with a list of the same request dictionaries.
Each query supplies its own `params.storage` and media settings. A successful response
contains individual job receipts in `queries`; save and track every accepted ID.
Use `client.account.limits()` to read your plan's current batch size.

## Bulk downloads

The SDK uses the management API to create a draft, upload an ID file to its signed
destination, and start the job. Media settings belong in `options`, including
`options.storage`. The toolkit's [bulk example](../examples/bulk_download.py) implements
that lifecycle and saves the ID before upload.

## Completion webhooks

Pass `callback_url="https://your-service.example/download-completed"` to
`submit_download`. It becomes a top-level query field, outside `params`.
FlashData notifies that public HTTPS endpoint when the job completes or fails.

The event contains a delivery ID, job ID, status and API links. Deduplicate notifications
by delivery ID. Callbacks are unsigned: verify the job through authenticated API reads
before acting on the notification. Keep polling as a fallback. This repository does not
start a public webhook server.

[Full download reference](https://flashdata.dev/docs/sources/youtube_download) ·
[Bulk reference](https://flashdata.dev/docs/reference/bulk-processing) ·
[Official SDK](https://github.com/flashdatadev/flashdata-python)
