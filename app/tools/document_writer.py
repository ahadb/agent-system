"""
Write plain-text files under a base directory (path-safe, like read_document).

Intended for notes, drafts, and agent-produced text — not binary uploads.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from app.tools.document_reader import _resolve_path

WriteMode = Literal["write", "append"]


def write_document(
    file_path: str,
    content: str,
    *,
    encoding: str = "utf-8",
    mode: WriteMode = "write",
    base_dir: str | None = None,
) -> dict[str, str | int]:
    """
    Write or append UTF-8 text at ``file_path`` relative to ``base_dir``.

    Parent directories are created as needed. Paths cannot escape ``base_dir``.
    """
    base_resolved = Path(base_dir).resolve() if base_dir else Path.cwd().resolve()
    try:
        path = _resolve_path(file_path, base_resolved)
    except ValueError as e:
        return {"error": str(e), "type": "error", "bytes_written": 0}

    # Avoid surprises with directories / odd paths after resolve
    if path.exists() and path.is_dir():
        return {"error": f"Path is a directory: {path}", "type": "error", "bytes_written": 0}

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append":
            with path.open("a", encoding=encoding) as f:
                n = f.write(content)
        else:
            with path.open("w", encoding=encoding) as f:
                n = f.write(content)
        return {
            "type": "text",
            "path": str(path.relative_to(base_resolved)),
            "bytes_written": n,
            "mode": mode,
        }
    except OSError as e:
        return {"error": str(e), "type": "error", "bytes_written": 0}
