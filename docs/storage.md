# Storage setup for YouTube downloads

The public API uploads media directly to a cloud destination. Configure it once in
Python and pass `storage=storage` to the examples. `storage_url` is the **bucket or
container name**, not a public URL. FlashData receives these credentials to write
the requested objects.

## Amazon S3

```python
storage = {
    "storage_type": "s3",
    "storage_url": "your-media-bucket",
    "region": "us-east-1",
    "object_prefix": "youtube/YYYYMMDD",
    "access_key": "your-storage-access-key",
    "secret_key": "your-storage-secret-key",
}
```

Use credentials with object-write access to the intended destination. Your account's
bucket policy and encryption configuration may require additional permissions.
`YYYYMMDD` expands to the UTC upload date. A fixed prefix such as `training/run-001`
is also supported.

## Cloudflare R2 and other S3-compatible storage

```python
storage = {
    "storage_type": "s3_compatible",
    "storage_url": "your-r2-bucket",
    "endpoint_url": "https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com",
    "region": "auto",
    "object_prefix": "youtube/YYYYMMDD",
    "access_key": "your-r2-access-key",
    "secret_key": "your-r2-secret-key",
}
```

For another S3-compatible provider, use its public HTTPS endpoint and required region.

## Other supported providers

| Provider | `storage_type` | Credential fields |
| --- | --- | --- |
| Google Cloud Storage | `gcs` | `service_account` object containing `project_id`, `client_email`, `private_key` |
| Azure Blob Storage | `azure` | `account_name`, container `sas_token` with write permission |
| Alibaba Cloud OSS | `oss` | `access_key`, `secret_key`, public `endpoint_url` |
| Tencent COS | `cos` | `access_key`, `secret_key`, `ap-*` region; bucket includes APPID |
| Baidu BOS | `bos` | `access_key`, `secret_key`, supported `region` |
| Volcengine TOS | `tos` | `access_key`, `secret_key`, supported `region` |

All also need `storage_url`. See the [provider-specific API examples](https://flashdata.dev/docs/sources/youtube_download#storage) for full fields and supported regions.

## Temporary credentials (STS)

With SDK 1.3 or later, single downloads and bulk downloads accept `session_token`
alongside the matching temporary `access_key` and `secret_key`:

```python
from flashdata import FlashData
from flashdata_download import submit_download

storage = {
    "storage_type": "s3",
    "storage_url": "your-media-bucket",
    "region": "us-east-1",
    "object_prefix": "youtube/YYYYMMDD",
    "access_key": "your-temporary-access-key",
    "secret_key": "your-temporary-secret-key",
    "session_token": "your-session-token",
}

with FlashData(api_key="your-flashdata-api-key") as client:
    job_id = submit_download(
        client,
        "dQw4w9WgXcQ",
        storage=storage,
        checkpoint="sts-download.job.json",
        output_format="mp4",
    )
    print(job_id)
```

The checkpoint saves the accepted job ID without storage credentials. Use the same
storage dictionary with `submit_bulk(..., storage=storage, ...)` or in the private
`examples/config.py` used by the recipes. The API receives it as `params.storage`
for a download and `options.storage` for a bulk download.

| `storage_type` | Temporary token supplied as `session_token` |
| --- | --- |
| `s3` | AWS STS `SessionToken` |
| `s3_compatible` | The provider's S3 session token, if supported |
| `oss` | Alibaba Cloud STS `SecurityToken` |
| `cos` | Tencent Cloud `Token`, with `TmpSecretId` / `TmpSecretKey` as the key pair |
| `bos` | Baidu Cloud STS session token |
| `tos` | Volcengine STS `SessionToken` |

For OSS, for example, keep its endpoint and use the STS key pair and token:

```python
storage = {
    "storage_type": "oss",
    "storage_url": "your-oss-bucket",
    "endpoint_url": "https://oss-cn-hangzhou.aliyuncs.com",
    "access_key": "your-temporary-access-key-id",
    "secret_key": "your-temporary-access-key-secret",
    "session_token": "your-security-token",
}
```

Keep each provider's normal bucket, endpoint and region fields. Omit `session_token`
for long-term keys, GCS and Azure. Tokens must be nonempty strings of at most 16,384
characters without whitespace or control characters. Their lifetime must cover
queueing, downloading, uploads and retries, including the whole bulk job. Neither
these examples nor FlashData automatically refresh temporary credentials.

## Read the delivered object

Use `results[0].file_url` to locate the media in your bucket. That URL may require
authentication. `file_size` is in bytes, and `md5` records the media checksum.
`upload_metadata=True` adds a companion metadata file described in `results[0].metadata`.

For S3/R2, install the optional storage dependency and fetch an object using its exact key:

```bash
python -m pip install -e ".[s3]"
python -m examples.fetch_from_s3 youtube/20261113/YOUR_OBJECT_NAME.mp4 --output output/video.mp4
```

Set the matching bucket credentials in `examples/config.py`. The local filename must
not already exist. Use the object key from your bucket or delivery record; filenames
can vary with output settings. Your storage credentials need read access for this step.

The S3 example passes `session_token` to boto3 as `aws_session_token` when present.
This also works with S3-compatible STS providers. Use credentials that are still
valid when fetching the object; credentials used earlier for delivery may have expired.

The server may use a different layout for metadata or clipped media. Do not construct
a filename from the video ID and assume that object exists.

## Store configuration privately

`examples/config.py`, `.env` files, `private-*.json`, checkpoints and `output/` are
gitignored. Checkpoints save only workflow information and job IDs. The SDK handles
authenticated result redirects without forwarding the API key to object storage.
