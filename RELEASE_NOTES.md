# FlashData YouTube Video Download API 0.2.0

Use optional `session_token` credentials with S3, S3-compatible storage, OSS,
COS, BOS and TOS. Storage examples cover temporary credentials, expiration and
renewal of paused bulk result delivery. GCS authentication is unchanged.

This release requires the official FlashData Python SDK 1.3.0 or newer.
Checkpoints keep job identifiers without saving API keys or storage credentials.
Existing storage configurations remain compatible.

The GitHub wheel and source archive are ready for manual PyPI publication.
If SDK 1.3.0 is not yet available on PyPI, install its verified release wheel first:

```sh
python -m pip install "https://github.com/flashdatadev/flashdata-python/releases/download/v1.3.0/flashdata-1.3.0-py3-none-any.whl#sha256=c28fc56a1ea11e930b313bb355792ebcd8c29d8d38d0ffd5d4b5a79e38c6b870"
```

The optional S3 fetch example forwards the session token to boto3 as `aws_session_token`.
