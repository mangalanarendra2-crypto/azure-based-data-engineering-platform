"""Ingest raw files into the ADLS Gen2 'landing' container.

Usage:
    python src/ingest_to_adls.py --file data/sample_orders.csv

Auth uses DefaultAzureCredential (az login locally, managed identity in Azure),
so no secrets live in code. Set AZURE_STORAGE_ACCOUNT in your environment.
"""
import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient


def get_service_client(account_name: str) -> DataLakeServiceClient:
    return DataLakeServiceClient(
        account_url=f"https://{account_name}.dfs.core.windows.net",
        credential=DefaultAzureCredential(),
    )


def upload_to_landing(account_name: str, local_file: Path, container: str = "landing") -> str:
    """Upload a file to landing/<dataset>/ingest_date=YYYY-MM-DD/<filename>."""
    dataset = local_file.stem
    ingest_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    remote_path = f"{dataset}/ingest_date={ingest_date}/{local_file.name}"

    fs = get_service_client(account_name).get_file_system_client(container)
    file_client = fs.get_file_client(remote_path)
    with local_file.open("rb") as fh:
        file_client.upload_data(fh, overwrite=True)

    return f"abfss://{container}@{account_name}.dfs.core.windows.net/{remote_path}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a file to the ADLS landing zone")
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--account", default=os.getenv("AZURE_STORAGE_ACCOUNT"))
    args = parser.parse_args()

    if not args.account:
        raise SystemExit("Provide --account or set AZURE_STORAGE_ACCOUNT")
    if not args.file.exists():
        raise SystemExit(f"File not found: {args.file}")

    print("Uploaded to:", upload_to_landing(args.account, args.file))


if __name__ == "__main__":
    main()
