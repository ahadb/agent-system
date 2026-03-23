"""
Approach 1: Single global registry (class-based).
Register tools explicitly with name, callable, description, and optional kwargs schema.
"""

from typing import Any, Callable, Literal

from pydantic import BaseModel, ValidationError

from app.config.settings import DOCS_BASE_PATH, WRITES_BASE_PATH
from app.tools.document_reader import read_document
from app.tools.document_writer import write_document


# Kwargs schemas per tool: validate LLM output before calling the tool.
class GetWeatherKwargs(BaseModel):
    city: str


class SearchDbKwargs(BaseModel):
    query: str
    limit: int = 10


class ReadDocumentKwargs(BaseModel):
    file_path: str
    encoding: str = "utf-8"


class WriteDocumentKwargs(BaseModel):
    file_path: str
    content: str
    encoding: str = "utf-8"
    mode: Literal["write", "append"] = "write"


class ToolRegistry:
    """Registry of tools: name -> (callable, description, optional kwargs model)."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}
        self._descriptions: dict[str, str] = {}
        self._kwargs_models: dict[str, type[BaseModel]] = {}

    def register(
        self,
        name: str,
        fn: Callable[..., Any],
        description: str,
        *,
        kwargs_model: type[BaseModel] | None = None,
    ) -> None:
        """Add a tool by name. Optionally provide a Pydantic model to validate kwargs."""
        self._tools[name] = fn
        self._descriptions[name] = description
        if kwargs_model is not None:
            self._kwargs_models[name] = kwargs_model

    def get(self, name: str) -> Callable[..., Any] | None:
        """Return the callable for a tool name, or None."""
        return self._tools.get(name)

    def validate_kwargs(self, name: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        """
        Validate kwargs against the tool's schema if one is registered.
        Returns validated kwargs (with defaults applied). Raises ValidationError if invalid.
        """
        model = self._kwargs_models.get(name)
        if model is None:
            return kwargs
        validated = model.model_validate(kwargs)
        return validated.model_dump()

    def run(self, name: str, **kwargs: Any) -> Any:
        """Run the tool by name with the given kwargs."""
        fn = self._tools.get(name)
        if fn is None:
            raise KeyError(f"Unknown tool: {name}")
        return fn(**kwargs)

    def get_descriptions(self) -> list[dict[str, str]]:
        """Return list of {name, description} for prompts."""
        return [
            {"name": n, "description": d}
            for n, d in self._descriptions.items()
        ]

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# Singleton instance; import and use this.
registry = ToolRegistry()

registry.register(
    "get_weather",
    lambda city: {"city": city, "temp": 72, "unit": "F"},
    "Get the current weather for a city. Args: city (str).",
    kwargs_model=GetWeatherKwargs,
)
registry.register(
    "search_db",
    lambda query, limit=10: [{"id": 1, "text": f"Result: {query}"}][:limit],
    "Search the database. Args: query (str), limit (int, optional, default 10).",
    kwargs_model=SearchDbKwargs,
)
def _read_document(file_path: str, encoding: str = "utf-8") -> Any:
    """Wrapper that injects DOCS_BASE_PATH so the agent only passes file_path (and optional encoding)."""
    return read_document(file_path, encoding=encoding, base_dir=DOCS_BASE_PATH)


registry.register(
    "read_document",
    _read_document,
    "Read a document from the filesystem. Supports .txt (plain text) and .pdf. Args: file_path (str, path relative to docs folder, e.g. sample.txt), encoding (str, optional, default utf-8 for text files). Returns content, type (text or pdf), and for PDFs pages.",
    kwargs_model=ReadDocumentKwargs,
)


def _write_document(
    file_path: str,
    content: str,
    encoding: str = "utf-8",
    mode: Literal["write", "append"] = "write",
) -> Any:
    return write_document(
        file_path,
        content,
        encoding=encoding,
        mode=mode,
        base_dir=WRITES_BASE_PATH,
    )


registry.register(
    "write_document",
    _write_document,
    "Write or append a UTF-8 text file under the configured writes directory. Args: file_path (str, relative path e.g. notes/out.txt), content (str), encoding (optional, default utf-8), mode (optional: write=overwrite, append=append). Creates parent folders as needed.",
    kwargs_model=WriteDocumentKwargs,
)
