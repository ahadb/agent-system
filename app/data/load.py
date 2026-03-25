from __future__ import annotations

import argparse
import json
from typing import Any

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from app.config import settings


def _project_id() -> str:
    if settings.GCP_PROJECT:
        return settings.GCP_PROJECT
    raise ValueError("GCP_PROJECT is required for load jobs.")


def ensure_dataset(client: bigquery.Client, dataset_id: str) -> None:
    dataset_ref = f"{client.project}.{dataset_id}"
    try:
        client.get_dataset(dataset_ref)
    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = settings.BQ_LOCATION
        client.create_dataset(dataset)


def destination_table_id(project_id: str) -> str:
    return f"{project_id}.{settings.BQ_DATASET_RAW}.{settings.BQ_TABLE_RAW}"


def run_load_job(*, source_uri: str, write_disposition: str = "WRITE_APPEND") -> dict[str, Any]:
    project_id = _project_id()
    client = bigquery.Client(project=project_id, location=settings.BQ_LOCATION)
    ensure_dataset(client, settings.BQ_DATASET_RAW)

    table_id = destination_table_id(project_id)
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=write_disposition,
        autodetect=True,
    )

    job = client.load_table_from_uri(source_uri, table_id, job_config=job_config)
    job.result()

    destination_table = client.get_table(table_id)
    return {
        "status": "ok",
        "source_uri": source_uri,
        "destination_table": table_id,
        "output_rows": destination_table.num_rows,
        "job_id": job.job_id,
        "write_disposition": write_disposition,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Load raw NDJSON from GCS into BigQuery raw table.")
    parser.add_argument(
        "--source-uri",
        required=True,
        help="GCS URI for NDJSON source file or wildcard, e.g. gs://bucket/raw/2026/03/24/*.json",
    )
    parser.add_argument(
        "--write-disposition",
        choices=["WRITE_APPEND", "WRITE_TRUNCATE", "WRITE_EMPTY"],
        default="WRITE_APPEND",
        help="BigQuery load write disposition. Default is WRITE_APPEND.",
    )
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()
    result = run_load_job(source_uri=args.source_uri, write_disposition=args.write_disposition)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
