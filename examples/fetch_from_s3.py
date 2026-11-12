"""Save a delivered S3/R2 object locally using your storage credentials."""

import argparse
from pathlib import Path

from ._shared import run, settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("object_key", help="Exact object key from your bucket/delivery result")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        import boto3
    except ImportError:
        raise ValueError(
            'Install the storage extra first: python -m pip install -e ".[s3]"'
        ) from None
    _, storage = settings()
    if storage["storage_type"] not in {"s3", "s3_compatible"}:
        raise ValueError("This example is for Amazon S3 and S3-compatible destinations such as R2.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    s3 = boto3.client(
        "s3",
        aws_access_key_id=storage["access_key"],
        aws_secret_access_key=storage["secret_key"],
        region_name=storage.get("region"),
        endpoint_url=storage.get("endpoint_url"),
    )
    with args.output.open("xb") as target:
        s3.download_fileobj(storage["storage_url"], args.object_key, target)
    print("Saved", args.output)


if __name__ == "__main__":
    run(main)
