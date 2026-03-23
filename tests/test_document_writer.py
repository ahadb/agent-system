"""Tests for write_document. Run: uv run pytest tests/test_document_writer.py -v"""

from pathlib import Path

from app.tools.document_writer import write_document


def test_write_creates_file(tmp_path: Path):
    result = write_document("out/notes.txt", "hello", base_dir=str(tmp_path))
    assert result["type"] == "text"
    assert result["bytes_written"] == 5
    assert result["mode"] == "write"
    path = tmp_path / "out" / "notes.txt"
    assert path.read_text() == "hello"


def test_append(tmp_path: Path):
    p = tmp_path / "log.txt"
    p.write_text("a")
    result = write_document("log.txt", "b", mode="append", base_dir=str(tmp_path))
    assert result["type"] == "text"
    assert result["mode"] == "append"
    assert p.read_text() == "ab"


def test_path_traversal_returns_error(tmp_path: Path):
    result = write_document("../../../etc/passwd", "x", base_dir=str(tmp_path))
    assert result["type"] == "error"
    assert result["bytes_written"] == 0


def test_write_rejects_existing_directory(tmp_path: Path):
    (tmp_path / "dir_only").mkdir()
    result = write_document("dir_only", "nope", base_dir=str(tmp_path))
    assert result["type"] == "error"
