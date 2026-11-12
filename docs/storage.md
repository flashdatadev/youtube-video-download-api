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

The server may use a different layout for metadata or clipped media. Do not construct
a filename from the video ID and assume that object exists.

## Store configuration privately

`examples/config.py`, `.env` files, `private-*.json`, checkpoints and `output/` are
gitignored. Checkpoints save only workflow information and job IDs. The SDK handles
authenticated result redirects without forwarding the API key to object storage.
