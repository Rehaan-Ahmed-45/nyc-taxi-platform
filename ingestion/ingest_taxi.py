import os
import sys
from pathlib import Path

import boto3
import requests
from botocore.client import Config
from dotenv import load_dotenv

# Load credentials from the .env file in the project root
load_dotenv()

ENDPOINT = "http://localhost:9000"
BUCKET = "bronze"
BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"


def download_file(year: int, month: int) -> Path:
    """Download one month of yellow taxi data to the local data/ folder."""
    filename = f"yellow_tripdata_{year}-{month:02d}.parquet"
    url = f"{BASE_URL}/{filename}"
    local_path = Path("data") / filename
    local_path.parent.mkdir(exist_ok=True)

    if local_path.exists():
        print(f"Already downloaded: {local_path}")
        return local_path

    print(f"Downloading {url} ...")
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()  # stops with a clear error on 404/403
        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)

    print(f"Saved {local_path} ({local_path.stat().st_size / 1e6:.1f} MB)")
    return local_path


def upload_to_bronze(local_path: Path, year: int, month: int) -> None:
    """Upload the file to the bronze bucket, untouched."""
    s3 = boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=os.environ["RUSTFS_ACCESS_KEY"],
        aws_secret_access_key=os.environ["RUSTFS_SECRET_KEY"],
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}),
    )

    # Partition-style folder layout, common in real data lakes
    key = f"yellow_taxi/year={year}/month={month:02d}/{local_path.name}"
    print(f"Uploading to s3://{BUCKET}/{key} ...")
    s3.upload_file(str(local_path), BUCKET, key)
    print("Upload complete.")


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    month = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    path = download_file(year, month)
    upload_to_bronze(path, year, month)