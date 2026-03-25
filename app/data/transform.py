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
    raise ValueError("GCP_PROJECT is required for transform jobs.")


def ensure_dataset(client: bigquery.Client, dataset_id: str) -> None:
    dataset_ref = f"{client.project}.{dataset_id}"
    try:
        client.get_dataset(dataset_ref)
    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = settings.BQ_LOCATION
        client.create_dataset(dataset)


def build_user_summary_sql(project_id: str) -> str:
    raw_table = f"`{project_id}.{settings.BQ_DATASET_RAW}.{settings.BQ_TABLE_RAW}`"
    summary_table = f"`{project_id}.{settings.BQ_DATASET_ANALYTICS}.{settings.BQ_TABLE_SUMMARY}`"
    return f"""
    CREATE OR REPLACE TABLE {summary_table} AS
    SELECT
      series_id,
      COUNT(*) AS event_count,
      SUM(value) AS total_value,
      AVG(value) AS avg_value,
      MIN(SAFE_CAST(date AS DATE)) AS first_observation_date,
      MAX(SAFE_CAST(date AS DATE)) AS last_observation_date,
      CURRENT_TIMESTAMP() AS transformed_at
    FROM {raw_table}
    WHERE series_id IS NOT NULL
    GROUP BY series_id
    """


def run_transform() -> dict[str, Any]:
    project_id = _project_id()
    client = bigquery.Client(project=project_id, location=settings.BQ_LOCATION)
    ensure_dataset(client, settings.BQ_DATASET_ANALYTICS)

    sql = build_user_summary_sql(project_id)
    job = client.query(sql)
    job.result()

    destination = f"{project_id}.{settings.BQ_DATASET_ANALYTICS}.{settings.BQ_TABLE_SUMMARY}"
    return {
        "status": "ok",
        "destination_table": destination,
        "job_id": job.job_id,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description="Run BigQuery SQL transforms for analytics tables.")


def main() -> None:
    parser = _build_arg_parser()
    parser.parse_args()
    result = run_transform()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
