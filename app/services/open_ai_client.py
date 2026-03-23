"""
OpenAI client for chat completions.

Uses configuration from app.config.settings. Wraps the call in asyncio.wait_for
for a timeout.
"""

import asyncio

from openai import AsyncOpenAI

from app.config.settings import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TIMEOUT_SECONDS


async def chat_with_usage(user_content: str) -> tuple[str, dict[str, int] | None]:
    """
    Send a single user message and return (content, token_usage).
    token_usage contains prompt_tokens, completion_tokens, total_tokens when available.
    """
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    async def _create() -> tuple[str, dict[str, int] | None]:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": user_content}],
        )
        content = (response.choices[0].message.content or "").strip()
        usage = getattr(response, "usage", None)
        if not usage:
            return content, None
        return content, {
            "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        }

    return await asyncio.wait_for(_create(), timeout=OPENAI_TIMEOUT_SECONDS)


async def chat(user_content: str) -> str:
    """
    Send a single user message and return the assistant's reply content.
    Raises asyncio.TimeoutError if the call exceeds OPENAI_TIMEOUT_SECONDS.
    """
    content, _usage = await chat_with_usage(user_content)
    return content
