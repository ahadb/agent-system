from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.config import settings


FRED_OBSERVATIONS_ENDPOINT = "https://api.stlouisfed.org/fred/series/observations"


class IngestionConfig(BaseModel):
    fred_api_key: str = Field(min_length=1)
    series_ids: list[str] = Field(min_length=1)
    observation_start: str | None = None
    observation_end: str | None = None
    local_raw_base_path: str
    upload_to_gcs: bool = False
    gcs_bucket_raw: str | None = None


def _parse_series_ids(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    return [part.strip() for part in raw_value.split(",") if part.strip()]


def load_ingestion_config() -> IngestionConfig:
    return IngestionConfig(
        fred_api_key=settings.FRED_API_KEY,
        series_ids=_parse_series_ids(settings.FRED_SERIES_IDS),
        observation_start=settings.FRED_OBSERVATION_START,
        observation_end=settings.FRED_OBSERVATION_END,
        local_raw_base_path=settings.LOCAL_RAW_BASE_PATH,
        upload_to_gcs=settings.UPLOAD_TO_GCS,
        gcs_bucket_raw=settings.GCS_BUCKET_RAW,
    )


def fetch_fred_observations(
    *,
    api_key: str,
    series_id: str,
    observation_start: str | None = None,
    observation_end: str | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, str] = {
        "api_key": api_key,
        "file_type": "json",
        "series_id": series_id,
        "limit": "100000",
    }
    if observation_start:
        params["observation_start"] = observation_start
    if observation_end:
        params["observation_end"] = observation_end

    response = httpx.get(FRED_OBSERVATIONS_ENDPOINT, params=params, timeout=30.0)
    response.raise_for_status()
    payload = response.json()

    observations = payload.get("observations", [])
    if not isinstance(observations, list):
        raise ValueError(f"Unexpected FRED response shape for series_id={series_id}")
    return observations


def _coerce_numeric(value: str) -> float | None:
    if value == ".":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def normalize_observations(series_id: str, observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ingested_at = dt.datetime.now(dt.timezone.utc).isoformat()
    records: list[dict[str, Any]] = []

    for item in observations:
        value = str(item.get("value", "."))
        date = str(item.get("date", ""))
        records.append(
            {
                "source": "fred",
                "series_id": series_id,
                "date": date,
                "value": _coerce_numeric(value),
                "value_raw": value,
                "ingested_at": ingested_at,
                "raw_observation": item,
            }
        )
    return records


def _partition_prefix(run_date: dt.date) -> str:
    return f"raw/{run_date:%Y/%m/%d}"


def write_local_ndjson(records: list[dict[str, Any]], base_path: str, run_date: dt.date) -> pathlib.Path:
    prefix = _partition_prefix(run_date)
    output_dir = pathlib.Path(base_path) / prefix
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"fred_events_{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}.json"
    output_path = output_dir / filename

    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    return output_path


def upload_file_to_gcs(local_path: pathlib.Path, bucket_name: str, blob_name: str) -> str:
    try:
        from google.cloud import storage  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-storage is not installed. Add it before enabling UPLOAD_TO_GCS."
        ) from exc

    client = storage.Client(project=settings.GCP_PROJECT or None)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(local_path))
    return f"gs://{bucket_name}/{blob_name}"


def run_ingestion(config: IngestionConfig) -> dict[str, Any]:
    all_records: list[dict[str, Any]] = []

    for series_id in config.series_ids:
        observations = fetch_fred_observations(
            api_key=config.fred_api_key,
            series_id=series_id,
            observation_start=config.observation_start,
            observation_end=config.observation_end,
        )
        all_records.extend(normalize_observations(series_id, observations))

    if not all_records:
        raise RuntimeError("No records fetched from FRED.")

    run_date = dt.datetime.now(dt.timezone.utc).date()
    local_path = write_local_ndjson(all_records, config.local_raw_base_path, run_date)

    result: dict[str, Any] = {
        "record_count": len(all_records),
        "local_path": str(local_path),
    }

    if config.upload_to_gcs:
        if not config.gcs_bucket_raw:
            raise ValueError("UPLOAD_TO_GCS is true but GCS_BUCKET_RAW is not set.")
        blob_name = f"{_partition_prefix(run_date)}/{local_path.name}"
        result["gcs_uri"] = upload_file_to_gcs(local_path, config.gcs_bucket_raw, blob_name)

    return result


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch FRED data and write raw JSON partition files.")
    parser.add_argument(
        "--upload-to-gcs",
        action="store_true",
        help="Upload written file to GCS bucket configured in GCS_BUCKET_RAW.",
    )
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    config = load_ingestion_config()
    if args.upload_to_gcs:
        config = config.model_copy(update={"upload_to_gcs": True})

    result = run_ingestion(config)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
