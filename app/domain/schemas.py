"""
Structured schemas for the agent "think" step (LLM decision).

Wire these to OpenAI/Vertex response_format / JSON schema next.
"""

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class AgentThinkToolCall(BaseModel):
    """Invoke one registered tool for the next step."""

    model_config = ConfigDict(extra="forbid")

    done: Literal[False] = False
    tool: str = Field(..., description="Registered tool name.")
    kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments validated against the tool schema.",
    )


class AgentThinkDone(BaseModel):
    """Stop the loop and return this answer to the user."""

    model_config = ConfigDict(extra="forbid")

    done: Literal[True]
    answer: str = Field(..., description="Final natural-language answer.")


# Discriminated union on `done` — use with TypeAdapter for parse/validate.
AgentThinkDecision = Annotated[
    Union[AgentThinkDone, AgentThinkToolCall],
    Field(discriminator="done"),
]
