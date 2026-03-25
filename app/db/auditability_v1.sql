BEGIN;

-- 1) One row per agent run
CREATE TABLE IF NOT EXISTS agent_runs (
  request_id           TEXT PRIMARY KEY,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  mode                  TEXT NOT NULL, -- 'task' | 'steps' | 'default'
  task                  TEXT NULL,      -- optional: original request.task (may be large)
  llm_provider          TEXT NULL,      -- 'openai' | 'vertex'
  llm_model             TEXT NULL,      -- e.g. 'gpt-4o-mini', 'gemini-2.5-flash'

  final_answer         TEXT NULL,
  error                 JSONB NULL,

  total_latency_ms     INTEGER NULL,

  -- Optional cost/usage fields (v1; fill later once both providers return usage reliably)
  prompt_tokens        BIGINT NULL,
  completion_tokens    BIGINT NULL,
  total_tokens         BIGINT NULL,
  cost_usd              NUMERIC NULL
);

-- 2) One row per tool decision + attempt
CREATE TABLE IF NOT EXISTS agent_steps (
  id                    BIGSERIAL PRIMARY KEY,

  request_id           TEXT NOT NULL REFERENCES agent_runs(request_id) ON DELETE CASCADE,
  step_index           INTEGER NOT NULL, -- 0..N-1 in loop order

  tool_name            TEXT NULL, -- NULL when the model finishes (done)
  tool_kwargs          JSONB NOT NULL DEFAULT '{}'::JSONB,

  status               TEXT NOT NULL, -- 'success' | 'validation_failed' | 'tool_failed' | 'unknown_tool'
  llm_think_latency_ms INTEGER NULL,
  tool_latency_ms      INTEGER NULL,

  -- Consider truncating/summarizing before storing; document/PDF payloads can be huge.
  tool_result          JSONB NULL,

  CONSTRAINT agent_steps_status_check
    CHECK (status IN ('success', 'validation_failed', 'tool_failed', 'unknown_tool')),

  CONSTRAINT agent_steps_request_step_unique
    UNIQUE (request_id, step_index)
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_agent_steps_request_id_step_index
  ON agent_steps (request_id, step_index);

CREATE INDEX IF NOT EXISTS idx_agent_runs_created_at
  ON agent_runs (created_at DESC);

COMMIT;

