"""
Unified LLM client used by the agent.

It can talk to either OpenAI or Vertex AI, selected via the LLM_PROVIDER
environment variable:

  LLM_PROVIDER=openai  (default)
  LLM_PROVIDER=vertex
"""

from __future__ import annotations

from typing import Literal

from app.config.settings import LLM_PROVIDER
from app.services.open_ai_client import chat as openai_chat
from app.services.open_ai_client import chat_with_usage as openai_chat_with_usage
from app.services.vertex_ai_client import chat as vertex_chat
from app.services.vertex_ai_client import chat_with_usage as vertex_chat_with_usage


Provider = Literal["openai", "vertex"]


def get_provider() -> Provider:
    """Return the resolved LLM provider (for storing in agent state, etc.)."""
    return "openai" if LLM_PROVIDER not in {"openai", "vertex"} else LLM_PROVIDER  # type: ignore[return-value]


async def chat(user_content: str) -> str:
    provider = get_provider()

    if provider == "vertex":
        return await vertex_chat(user_content)
    # Default: OpenAI
    return await openai_chat(user_content)


async def chat_with_usage(user_content: str) -> tuple[str, dict[str, int] | None]:
    """Return (content, token_usage) for the resolved provider."""
    provider = get_provider()
    if provider == "vertex":
        return await vertex_chat_with_usage(user_content)
    return await openai_chat_with_usage(user_content)

