"""
Vertex AI client for chat-like completions.

Uses GenerativeModel (Gemini); set VERTEX_MODEL to a current model (e.g. gemini-2.0-flash-001).
Assumes Application Default Credentials (ADC) are available:
- On Cloud Run: the service account's credentials are used automatically.
- Locally: run `gcloud auth application-default login` or use a service account key.
"""

from __future__ import annotations

import asyncio

import vertexai
from vertexai.generative_models import GenerativeModel

from app.config.settings import VERTEX_LOCATION, VERTEX_MODEL, VERTEX_PROJECT


async def chat_with_usage(user_content: str) -> tuple[str, dict[str, int] | None]:
    """
    Send a single user message and return (content, token_usage).

    token_usage contains prompt_tokens, completion_tokens, total_tokens when available.
    """
    if not (VERTEX_PROJECT and VERTEX_PROJECT.strip()):
        raise ValueError(
            "VERTEX_PROJECT must be set when using Vertex AI (e.g. in .env or environment). "
            "Example: VERTEX_PROJECT=your-gcp-project-id"
        )

    def _sync_call() -> tuple[str, dict[str, int] | None]:
        vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
        model = GenerativeModel(VERTEX_MODEL)
        response = model.generate_content(user_content)

        content = (response.text or "").strip()

        usage = getattr(response, "usage_metadata", None)
        if not usage:
            return content, None

        # Vertex fields vary slightly by SDK version; handle best-effort.
        prompt_tokens = getattr(usage, "prompt_token_count", None)
        total_tokens = getattr(usage, "total_token_count", None)
        candidates_tokens = getattr(usage, "candidates_token_count", None)

        prompt_tokens_i = int(prompt_tokens) if prompt_tokens is not None else None
        total_tokens_i = int(total_tokens) if total_tokens is not None else None
        completion_tokens_i = (
            int(candidates_tokens) if candidates_tokens is not None else None
        )

        # If only total + prompt are present, infer completion.
        if completion_tokens_i is None and prompt_tokens_i is not None and total_tokens_i is not None:
            completion_tokens_i = max(0, total_tokens_i - prompt_tokens_i)

        if prompt_tokens_i is None and total_tokens_i is None and completion_tokens_i is None:
            return content, None

        return content, {
            "prompt_tokens": int(prompt_tokens_i or 0),
            "completion_tokens": int(completion_tokens_i or 0),
            "total_tokens": int(total_tokens_i or 0),
        }

    return await asyncio.to_thread(_sync_call)


async def chat(user_content: str) -> str:
    """
    Send a single user message and return the model's reply content.

    This is intentionally simple: a single-turn prompt that treats the input
    as user content and returns a plain string response.
    """
    content, _usage = await chat_with_usage(user_content)
    return content

