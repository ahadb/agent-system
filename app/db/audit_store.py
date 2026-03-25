"""
Persistence helpers for auditability (agent_runs + agent_steps).

This is intentionally small for the initial local verification step.
"""

from __future__ import annotations

import os
from typing import Any

from psycopg2.extras import Json

from app.db.connection import get_connection


def _llm_model_for_provider(llm_provider: str | None) -> str | None:
    if llm_provider == "openai":
        return os.getenv("OPENAI_MODEL")
    if llm_provider == "vertex":
        return os.getenv("VERTEX_MODEL")
    return None


def insert_agent_run(
    *,
    request_id: str,
    mode: str,
    task: str | None,
    llm_provider: str | None,
) -> None:
    llm_model = _llm_model_for_provider(llm_provider)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_runs (request_id, mode, task, llm_provider, llm_model)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (request_id) DO UPDATE SET
                  mode = EXCLUDED.mode,
                  task = EXCLUDED.task,
                  llm_provider = EXCLUDED.llm_provider,
                  llm_model = EXCLUDED.llm_model;
                """,
                (request_id, mode, task, llm_provider, llm_model),
            )
        conn.commit()
    finally:
        conn.close()


def update_agent_run_final(
    *,
    request_id: str,
    final_answer: str | None,
    error: dict[str, Any] | None,
    total_latency_ms: int | None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE agent_runs
                SET final_answer = %s,
                    error = %s,
                    total_latency_ms = %s,
                    prompt_tokens = %s,
                    completion_tokens = %s,
                    total_tokens = %s
                WHERE request_id = %s;
                """,
                (
                    final_answer,
                    Json(error) if error is not None else None,
                    total_latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    request_id,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def insert_agent_step(
    *,
    request_id: str,
    step_index: int,
    tool_name: str | None,
    tool_kwargs: dict[str, Any],
    status: str,
    llm_think_latency_ms: int | None,
    tool_latency_ms: int | None,
) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_steps (
                  request_id,
                  step_index,
                  tool_name,
                  tool_kwargs,
                  status,
                  llm_think_latency_ms,
                  tool_latency_ms,
                  tool_result
                )
                VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, NULL);
                """,
                (
                    request_id,
                    step_index,
                    tool_name,
                    Json(tool_kwargs),
                    status,
                    llm_think_latency_ms,
                    tool_latency_ms,
                ),
            )
        conn.commit()
    finally:
        conn.close()

