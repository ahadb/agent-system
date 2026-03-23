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

# Document reader: base directory for read_document (paths relative to this). Empty = cwd.
DOCS_BASE_PATH: str | None = os.getenv("DOCS_BASE_PATH") or None

# Writes from write_document; falls back to DOCS_BASE_PATH then cwd when unset.
WRITES_BASE_PATH: str | None = os.getenv("WRITES_BASE_PATH") or os.getenv("DOCS_BASE_PATH") or None

