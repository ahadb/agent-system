"""
Agent loop: think → act → observe, repeated until the task is done.

  Think: Decide what to do next (call a tool or finish). Uses the LLM when a task
         is given; otherwise uses a provided list of steps or a default.
  Act:   Run the chosen tool with its arguments.
  Observe: Store the tool result in state, then loop back to think.
"""

from typing import Any, Callable, TypeAlias, cast
import time
import os

import structlog
from pydantic import TypeAdapter, ValidationError

from app.domain.prompts import build_agent_think_prompt
from app.domain.schemas import AgentThinkDone, AgentThinkToolCall
from app.services.llm_client import chat_with_usage as llm_chat_with_usage, get_provider as get_llm_provider
from app.tools.global_registry import registry
from app.utils.parse_response import _parse_llm_response
from db.audit_store import insert_agent_run, insert_agent_step, update_agent_run_final

logger = structlog.get_logger()

# Shape: {"tool": str, "kwargs": dict}. Used for each step in the loop.
NextToolCall: TypeAlias = dict[str, Any]

_think_decision_adapter = TypeAdapter(AgentThinkDone | AgentThinkToolCall)


async def llm_think(task: str, state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int] | None]:
    """
    Ask the LLM what to do next. Parses JSON then validates against AgentThinkDecision.
    Returns either {"tool": str, "kwargs": dict} or {"done": True, "answer": str}.
    """
    prompt = build_agent_think_prompt(task, state, registry.get_descriptions())
    content, usage = await llm_chat_with_usage(prompt)
    raw = _parse_llm_response(content)
    try:
        decision = _think_decision_adapter.validate_python(raw)
    except ValidationError as e:
        logger.error(
            "llm_think_schema_validation_failed",
            errors=e.errors(),
            raw_keys=list(raw.keys()) if isinstance(raw, dict) else None,
        )
        raise
    if isinstance(decision, AgentThinkDone):
        return {"done": True, "answer": decision.answer}, usage
    return {"tool": decision.tool, "kwargs": decision.kwargs}, usage


def default_think(s: dict[str, Any], i: int) -> dict[str, Any] | None:
    if i == 0:
        return {"tool": "get_weather", "kwargs": {"city": "Boston"}}
    return None


def act(tool_name: str, **kwargs: Any) -> Any:
    """Execute the tool via the global registry."""
    return registry.run(tool_name, **kwargs)


def observe(state: dict[str, Any], tool_name: str, result: Any) -> None:
    """Record what happened. Update state with the result."""
    if "results" not in state:
        state["results"] = []
    state["results"].append({"tool": tool_name, "result": result})


def _get_tool_and_kwargs(next_tool_call: Any) -> tuple[str, dict[str, Any]]:
    """Get tool name and kwargs from either a dict or an object with .tool / .kwargs."""
    if hasattr(next_tool_call, "get") and callable(next_tool_call.get):
        return next_tool_call["tool"], cast(dict[str, Any], next_tool_call.get("kwargs", {}))
    kwargs = cast(dict[str, Any], getattr(next_tool_call, "kwargs", None) or {})
    return getattr(next_tool_call, "tool"), kwargs


async def run_agent_loop(
    steps: list[NextToolCall] | None = None,
    *,
    task: str | None = None,
    request_id: str | None = None,
    think: Callable[[dict[str, Any], int], NextToolCall | None] | None = None,
    max_steps: int = 10,
) -> dict[str, Any]:
    """
    Run think → act → observe until done or max_steps.

    Each iteration:
      Think  — decide next action (tool + kwargs, or done with final answer).
      Act    — run the tool.
      Observe — append the result to state.

    How "think" is chosen: steps list (no LLM), task (LLM), custom think(), or default.
    """
    state: dict[str, Any] = {}
    run_started_at = time.monotonic()
    prompt_tokens_total: int | None = None
    completion_tokens_total: int | None = None
    total_tokens_total: int | None = None
    if request_id is not None:
        state["request_id"] = request_id
    if task:
        state["llm_provider"] = get_llm_provider()

    # Audit: create run row as early as possible (only if request_id is present).
    if request_id is not None:
        mode = "steps" if steps is not None else ("task" if task else "default")
        llm_provider = state.get("llm_provider")
        try:
            insert_agent_run(
                request_id=request_id,
                mode=mode,
                task=task,
                llm_provider=llm_provider,
            )
        except Exception as e:
            logger.warning("audit_insert_run_failed", request_id=request_id, error=str(e), exc_info=True)

    step = 0

    while step < max_steps:
        next_tool_call: NextToolCall | None = None

        if steps is not None:
            # Predefined steps: use the next step from the list. No LLM.
            if step >= len(steps):
                break
            next_tool_call = steps[step]
        elif task:
            # Task given: ask the LLM. It returns a tool call or "done" with final answer.
            try:
                llm_think_started_at = time.monotonic()
                decision, usage = await llm_think(task, state)
                llm_think_latency_ms = int((time.monotonic() - llm_think_started_at) * 1000)
            except Exception as e:
                logger.error(
                    "llm_think_failed",
                    request_id=request_id,
                    step=step,
                    error=str(e),
                    exc_info=True,
                )
                raise
            # Accumulate token usage across all LLM think steps (including the final 'done').
            if usage:
                prompt_tokens_total = (prompt_tokens_total or 0) + usage.get("prompt_tokens", 0)
                completion_tokens_total = (completion_tokens_total or 0) + usage.get("completion_tokens", 0)
                total_tokens_total = (total_tokens_total or 0) + usage.get("total_tokens", 0)

            if decision.get("done"):
                state["final_answer"] = decision.get("answer", "")
                break
            next_tool_call = {
                "tool": decision["tool"],
                "kwargs": decision.get("kwargs", {}),
            }
        else:
            # No steps, no task: use a custom think() or the default (one get_weather then stop).
            default_tool = think if think is not None else default_think
            next_tool_call = default_tool(state, step)
            if next_tool_call is None:
                break

        if next_tool_call is None:
            break

        tool_name, kwargs = _get_tool_and_kwargs(next_tool_call)

        # Think: log the chosen action for this step.
        logger.info(
            "agent_think",
            request_id=request_id,
            step=step,
            tool=tool_name,
        )

        if tool_name not in registry:
            logger.warning(
                "unknown_tool",
                request_id=request_id,
                step=step,
                tool=tool_name,
            )
            if request_id is not None:
                try:
                    insert_agent_step(
                        request_id=request_id,
                        step_index=step,
                        tool_name=tool_name,
                        tool_kwargs=kwargs,
                        status="unknown_tool",
                        llm_think_latency_ms=locals().get("llm_think_latency_ms"),
                        tool_latency_ms=None,
                    )
                except Exception as e:
                    logger.warning("audit_insert_step_failed", request_id=request_id, error=str(e), exc_info=True)
            state["error"] = {"type": "unknown_tool", "tool": tool_name, "message": f"Unknown tool: {tool_name}"}
            break

        try:
            validated_kwargs = registry.validate_kwargs(tool_name, kwargs)
        except ValidationError as e:
            logger.warning(
                "tool_kwargs_validation_failed",
                request_id=request_id,
                step=step,
                tool=tool_name,
                errors=e.errors(),
            )
            observe(state, tool_name, {"error": "Invalid arguments", "details": e.errors()})
            logger.info(
                "agent_observe",
                request_id=request_id,
                step=step,
                tool=tool_name,
                success=False,
            )
            if request_id is not None:
                try:
                    insert_agent_step(
                        request_id=request_id,
                        step_index=step,
                        tool_name=tool_name,
                        tool_kwargs=kwargs,
                        status="validation_failed",
                        llm_think_latency_ms=locals().get("llm_think_latency_ms"),
                        tool_latency_ms=None,
                    )
                except Exception as e:
                    logger.warning("audit_insert_step_failed", request_id=request_id, error=str(e), exc_info=True)
            step += 1
            continue

        try:
            logger.info(
                "agent_act_start",
                request_id=request_id,
                step=step,
                tool=tool_name,
            )
            tool_started_at = time.monotonic()
            result = act(tool_name, **validated_kwargs)
            tool_latency_ms = int((time.monotonic() - tool_started_at) * 1000)
            observe(state, tool_name, result)
            logger.info(
                "agent_observe",
                request_id=request_id,
                step=step,
                tool=tool_name,
                success=True,
            )
            if request_id is not None:
                try:
                    insert_agent_step(
                        request_id=request_id,
                        step_index=step,
                        tool_name=tool_name,
                        tool_kwargs=validated_kwargs,
                        status="success",
                        llm_think_latency_ms=locals().get("llm_think_latency_ms"),
                        tool_latency_ms=tool_latency_ms,
                    )
                except Exception as e:
                    logger.warning("audit_insert_step_failed", request_id=request_id, error=str(e), exc_info=True)
        except Exception as e:
            logger.warning(
                "tool_failed",
                request_id=request_id,
                step=step,
                tool=tool_name,
                error=str(e),
                exc_info=True,
            )
            observe(state, tool_name, {"error": str(e)})
            logger.info(
                "agent_observe",
                request_id=request_id,
                step=step,
                tool=tool_name,
                success=False,
            )
            if request_id is not None:
                try:
                    insert_agent_step(
                        request_id=request_id,
                        step_index=step,
                        tool_name=tool_name,
                        tool_kwargs=kwargs,
                        status="tool_failed",
                        llm_think_latency_ms=locals().get("llm_think_latency_ms"),
                        tool_latency_ms=None,
                    )
                except Exception as e:
                    logger.warning("audit_insert_step_failed", request_id=request_id, error=str(e), exc_info=True)
        step += 1

    # Audit: update run final outcome.
    if request_id is not None:
        total_latency_ms = int((time.monotonic() - run_started_at) * 1000)
        try:
            update_agent_run_final(
                request_id=request_id,
                final_answer=state.get("final_answer"),
                error=state.get("error"),
                total_latency_ms=total_latency_ms,
                prompt_tokens=prompt_tokens_total,
                completion_tokens=completion_tokens_total,
                total_tokens=total_tokens_total,
            )
        except Exception as e:
            logger.warning(
                "audit_update_run_failed",
                request_id=request_id,
                error=str(e),
                exc_info=True,
            )

    return state