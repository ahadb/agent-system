## Agent System

An enterprise-oriented agent orchestration service that runs a controlled think -> act -> observe loop, enforces schema-validated tool execution, and captures auditable run/step telemetry for reliability, governance, and production operations.

## Cloud First (High Priority)

Cloud deployment is a core requirement for this project.

- Designed to run in cloud environments (especially GCP/Cloud Run).
- Supports cloud LLM provider integration via Vertex AI.
- Includes Postgres-backed auditability designed to carry from local to managed cloud DB.

## High-Level Architecture

```
FastAPI API
  (/agent) 
     |
     v
Agent Loop (think → act → observe)
  - Think: LLM returns JSON {tool, kwargs} or {done, answer}
  - Act: tool execution via global tool registry (Pydantic kwargs validation)
  - Observe: append tool results to state
     |
     +--> Audit persistence (Postgres): agent_runs + agent_steps
     |
     +--> Structured logs (structlog)
```

## Main Components

- `app/main.py`: FastAPI entrypoint (`/`, `/health`, `/agent`).
- `app/agent.py`: core think -> act -> observe loop.
- `app/tools/global_registry.py`: tool registry + kwargs schema validation.
- `app/services/`: OpenAI/Vertex clients behind one LLM interface.
- `db/`: Postgres pooling + audit writes (`agent_runs`, `agent_steps`).

## Run with Docker

```bash
docker build -t agent-system-app .
docker network create agent-net

docker run -d \
  --name agent-postgres \
  --network agent-net \
  -e POSTGRES_DB=agent_system \
  -e POSTGRES_USER=agent_user \
  -e POSTGRES_PASSWORD=agent_pass \
  -p 5433:5432 \
  postgres:16

docker run -d \
  --name agent-app \
  --network agent-net \
  -e PG_HOST=agent-postgres \
  -e PG_PORT=5432 \
  -e PG_DATABASE=agent_system \
  -e PG_USER=agent_user \
  -e PG_PASSWORD=agent_pass \
  -e LLM_PROVIDER=openai \
  -e OPENAI_API_KEY=your_openai_key_here \
  -p 8080:8080 \
  agent-system-app
```

## Running / API Contract (Brief)

Start the server (example):
`uvicorn app.main:app --reload`

`POST /agent` request body (one of the following):
```json
{ "task": "What is the weather in Boston?" }
```
```json
{ "steps": [ { "tool": "get_weather", "kwargs": { "city": "Boston" } } ] }
```

Response shape:
`{ "results": [...], "final_answer": "...", "error": {...} , "llm_provider": "openai|vertex" }`

## Environment (Most Relevant)

LLM:
- `LLM_PROVIDER` (`openai` or `vertex`)
- OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL`
- Vertex: `VERTEX_PROJECT`, `VERTEX_LOCATION`, `VERTEX_MODEL`

Tool file access scoping:
- `DOCS_BASE_PATH` (for `read_document`)
- `WRITES_BASE_PATH` (for `write_document`)

Postgres audit:
- `PG_HOST`, `PG_PORT`, `PG_DATABASE` (or `DB_*` aliases), `PG_USER`, `PG_PASSWORD`, `PG_SSL_MODE`

