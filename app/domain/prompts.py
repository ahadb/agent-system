import textwrap
from typing import Any


def build_agent_think_prompt(
    task: str,
    state: dict[str, Any],
    tool_descriptions: list[dict[str, str]],
) -> str:
    """
    Build the full prompt for the agent think step. Formats state and tools
    and returns the string to send to the LLM.
    """
    results = state.get("results", [])
    state_summary = (
        "No previous actions yet."
        if not results
        else "\n".join(
            f"Tool: {r['tool']}, Result: {r['result']}" for r in results
        )
    )
    tools_blob = "\n".join(
        f"- {t['name']}: {t['description']}" for t in tool_descriptions
    )
    return textwrap.dedent(f"""\
        You are an agent. Given the task and current state, decide the next action.

        Task: {task}

        Previous actions and results:
        {state_summary}

        Available tools:
        {tools_blob}

        Respond with JSON only, no other text. Choose one:
        - To call a tool: {{"tool": "<tool_name>", "kwargs": {{...}}}}
        - To finish: {{"done": true, "answer": "<your final answer to the user>"}}
    """)
