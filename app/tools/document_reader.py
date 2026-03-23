"""
Document reader tool: read plain text and PDF files.

Uses open() for text and pypdf for PDFs. Paths are resolved against a base
directory to avoid path traversal; base defaults to current working directory.
"""

from pathlib import Path

from pypdf import PdfReader


def _resolve_path(file_path: str, base_dir: Path | None = None) -> Path:
    base = base_dir or Path.cwd()
    base = base.resolve()
    resolved = (base / file_path).resolve()
    if not resolved.is_relative_to(base):
        raise ValueError(f"Path escapes base directory: {file_path}")
    return resolved


def read_document(
    file_path: str,
    encoding: str = "utf-8",
    base_dir: str | None = None,
) -> dict[str, str | int]:
    base = Path(base_dir).resolve() if base_dir else None
    try:
        path = _resolve_path(file_path, base)
    except ValueError as e:
        return {"error": str(e), "content": "", "type": "error"}

    if not path.exists():
        return {"error": f"File not found: {path}", "content": "", "type": "error"}
    if not path.is_file():
        return {"error": f"Not a file: {path}", "content": "", "type": "error"}

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            reader = PdfReader(path)
            text_parts = []
            for page in reader.pages:
                part = page.extract_text()
                if part:
                    text_parts.append(part)
            content = "\n".join(text_parts) or "(no text extracted)"
            return {
                "content": content,
                "type": "pdf",
                "pages": len(reader.pages),
            }
        except Exception as e:
            return {"error": str(e), "content": "", "type": "error"}
    else:
        # Treat as text (e.g. .txt or no extension)
        try:
            content = path.read_text(encoding=encoding)
            return {"content": content, "type": "text"}
        except Exception as e:
            return {"error": str(e), "content": "", "type": "error"}
