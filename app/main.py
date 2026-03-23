from typing import Any
from uuid import uuid4

import structlog
from fastapi import FastAPI
from pydantic import BaseModel

from app.agent import run_agent_loop
from app.config.logging_config import configure_logging

from app.services.llm_client import get_provider

configure_logging(json_logs=True)
logger = structlog.get_logger()

app = FastAPI()


class Step(BaseModel):
    tool: str
    kwargs: dict[str, Any] = {}


class AgentRequest(BaseModel):
    task: str | None = None  # If set, LLM decides each step. Otherwise use steps.
    steps: list[Step] | None = None  # Optional predefined steps (no LLM).

class AgentResponse(BaseModel):
    results: list[dict[str, Any]] = []
    final_answer: str | None = None
    error: dict[str, Any] | None = None
    llm_provider: str | None = None


@app.get("/")
def root():
    return {"message": "ok"}

@app.get("/health")
def health():
    provider = get_provider()
    return {"status": "healthy", "provider": provider}


@app.post(
    "/agent",
    summary="Run the agent loop",
    description="""
Three ways to run, depending on the payload:

**1. Predefined steps (no LLM)** — send `steps` only:
```json
{
  "steps": [
    { "tool": "get_weather", "kwargs": { "city": "Boston" } },
    { "tool": "search_db", "kwargs": { "query": "coffee", "limit": 5 } }
  ]
}
```

**2. Task (LLM decides each step)** — send `task` only:
```json
{
  "task": "What is the weather in Boston and search the db for coffee?"
}
```

**3. Default think (mock)** — send neither, or empty body:
```json
{}
```
Runs one get_weather for Boston then stops.
""",
)
async def agent(request: AgentRequest) -> AgentResponse:
    request_id = str(uuid4())

    if request.task is not None:
        mode = "task"
        logger.info("agent_request", request_id=request_id, mode=mode, task=request.task)
        state = await run_agent_loop(task=request.task, request_id=request_id)
    elif request.steps:
        mode = "steps"
        logger.info("agent_request", request_id=request_id, mode=mode, steps_count=len(request.steps))
        steps_as_dicts = [s.model_dump() for s in request.steps]
        state = await run_agent_loop(steps=steps_as_dicts, request_id=request_id)
    else:
        mode = "default"
        logger.info("agent_request", request_id=request_id, mode=mode)
        state = await run_agent_loop(request_id=request_id)  # default mock think

    logger.info(
        "agent_response",
        request_id=request_id,
        results_count=len(state.get("results", [])),
        has_final_answer=bool(state.get("final_answer")),
        has_error=bool(state.get("error")),
    )
    return AgentResponse(
        results=state.get("results", []),
        final_answer=state.get("final_answer"),
        error=state.get("error"),
        llm_provider=state.get("llm_provider"),
    )
