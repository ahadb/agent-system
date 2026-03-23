"""
Approach 2: Decorator-based registration.
Use @tool("name", description="...") on a function; it registers itself on import.
"""

from typing import Any, Callable

# Registry: name -> (callable, description)
_tools: dict[str, tuple[Callable[..., Any], str]] = {}


def tool(name: str, description: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that registers a function as a tool."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        _tools[name] = (fn, description)
        return fn

    return decorator


def get(name: str) -> Callable[..., Any] | None:
    """Return the callable for a tool name, or None."""
    entry = _tools.get(name)
    return entry[0] if entry else None


def run(name: str, **kwargs: Any) -> Any:
    """Run the tool by name with the given kwargs."""
    entry = _tools.get(name)
    if entry is None:
        raise KeyError(f"Unknown tool: {name}")
    fn, _ = entry
    return fn(**kwargs)


def get_descriptions() -> list[dict[str, str]]:
    """Return list of {name, description} for prompts."""
    return [
        {"name": n, "description": d}
        for n, (_, d) in _tools.items()
    ]


# Example: define tools with the decorator (register when this module is imported).
@tool("get_weather", "Get the current weather for a city. Args: city (str).")
def get_weather(city: str) -> dict[str, Any]:
    return {"city": city, "temp": 72, "unit": "F"}


@tool("search_db", "Search the database. Args: query (str), limit (int, optional, default 10).")
def search_db(query: str, limit: int = 10) -> list[dict[str, Any]]:
    return [{"id": 1, "text": f"Result: {query}"}][:limit]
