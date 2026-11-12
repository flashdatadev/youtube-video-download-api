"""Copy to examples/config.py and replace placeholders. That private file is gitignored."""

API_KEY = "your-flashdata-api-key"

STORAGE = {
    "storage_type": "s3",
    "storage_url": "your-media-bucket",
    "region": "us-east-1",
    "object_prefix": "youtube-downloads/YYYYMMDD",
    "access_key": "your-storage-access-key",
    "secret_key": "your-storage-secret-key",
}
