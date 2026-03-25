"""
Central place to read environment-based configuration for the app.

Right now we keep LLM-related settings here so other modules
don't reach into os.environ directly. Loads .env from the project root
when present (e.g. when running locally with uv/uvicorn).
"""

import os

from dotenv import load_dotenv

load_dotenv()

# LLM provider selection: "openai" (default) or "vertex"
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower()

# OpenAI settings
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT_SECONDS: float = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))

# Vertex AI settings
VERTEX_PROJECT: str | None = os.getenv("VERTEX_PROJECT") or None
VERTEX_LOCATION: str = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_MODEL: str = os.getenv("VERTEX_MODEL", "gemini-2.0-flash-001")

# Postgres settings
PG_HOST: str = os.getenv("PG_HOST") or os.getenv("DB_HOST") or "localhost"
PG_PORT: int = int(os.getenv("PG_PORT") or os.getenv("DB_PORT") or "5433")
PG_DATABASE: str = (
    os.getenv("PG_DATABASE")
    or os.getenv("PG_NAME")
    or os.getenv("DB_NAME")
    or "agent_system"
)
PG_USER: str = os.getenv("PG_USER") or os.getenv("DB_USER") or "ahadbokhari"
PG_PASSWORD: str = os.getenv("PG_PASSWORD") or os.getenv("DB_PASSWORD") or ""
PG_SSL_MODE: str = os.getenv("PG_SSL_MODE") or os.getenv("DB_SSL_MODE") or ""
PGPOOL_MIN: int = int(os.getenv("PGPOOL_MIN", "1"))
PGPOOL_MAX: int = int(os.getenv("PGPOOL_MAX", "10"))

# Document reader: base directory for read_document (paths relative to this). Empty = cwd.
DOCS_BASE_PATH: str | None = os.getenv("DOCS_BASE_PATH") or None

# Writes from write_document; falls back to DOCS_BASE_PATH then cwd when unset.
WRITES_BASE_PATH: str | None = os.getenv("WRITES_BASE_PATH") or os.getenv("DOCS_BASE_PATH") or None

# Data pipeline / GCP settings
GCP_PROJECT: str | None = os.getenv("GCP_PROJECT") or None
GCP_LOCATION: str = os.getenv("GCP_LOCATION", "us-central1")
GOOGLE_APPLICATION_CREDENTIALS: str | None = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or None

# Cloud Storage raw data landing zone
GCS_BUCKET_RAW: str | None = os.getenv("GCS_BUCKET_RAW") or None

# BigQuery settings
BQ_LOCATION: str = os.getenv("BQ_LOCATION", "US")
BQ_DATASET_RAW: str = os.getenv("BQ_DATASET_RAW", "raw_data")
BQ_TABLE_RAW: str = os.getenv("BQ_TABLE_RAW", "raw_events")
BQ_DATASET_ANALYTICS: str = os.getenv("BQ_DATASET_ANALYTICS", "analytics")
BQ_TABLE_SUMMARY: str = os.getenv("BQ_TABLE_SUMMARY", "user_summary")

# External source for ingestion
PIPELINE_SOURCE_URL: str | None = os.getenv("PIPELINE_SOURCE_URL") or None

# FRED ingestion settings
FRED_API_KEY: str = os.getenv("FRED_API_KEY", "").strip()
FRED_SERIES_IDS: str | None = os.getenv("FRED_SERIES_IDS") or None
FRED_OBSERVATION_START: str | None = os.getenv("FRED_OBSERVATION_START") or None
FRED_OBSERVATION_END: str | None = os.getenv("FRED_OBSERVATION_END") or None
LOCAL_RAW_BASE_PATH: str = os.getenv("LOCAL_RAW_BASE_PATH", "data/raw").strip() or "data/raw"
UPLOAD_TO_GCS: bool = (os.getenv("UPLOAD_TO_GCS", "").strip().lower() in {"1", "true", "yes", "y", "on"})

