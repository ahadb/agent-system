"""
Minimal tests for the read_document tool.

Run from project root: uv run pytest tests/test_document_reader.py -v
"""

from pathlib import Path

from pypdf import PdfWriter

from app.tools.document_reader import read_document

# Directory where this test file lives; fixtures live next to it.
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_read_text_file():
    """Read a .txt file: returns type 'text' and the file content."""
    result = read_document("sample.txt", base_dir=str(FIXTURES_DIR))
    assert result["type"] == "text"
    content = result["content"]
    assert isinstance(content, str) and "NovaTech Solutions experienced strong growth in the first quarter of 2026" in content


def test_read_pdf_file(tmp_path):
    """Read a .pdf file: returns type 'pdf', content, and page count."""
    # Create a minimal one-page PDF on the fly (no binary fixture needed)
    pdf_path = tmp_path / "minimal.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(pdf_path)

    result = read_document("minimal.pdf", base_dir=str(tmp_path))
    assert result["type"] == "pdf"
    assert result["pages"] == 1
    assert "content" in result


def test_missing_file_returns_error():
    """A missing path returns type 'error' and an error message."""
    result = read_document("does_not_exist.txt", base_dir=str(FIXTURES_DIR))
    assert result["type"] == "error"
    assert "error" in result
    assert result["content"] == ""


def test_path_traversal_returns_error():
    """Path that escapes base dir (e.g. ..) returns error, not file content."""
    result = read_document("../../../etc/passwd", base_dir=str(FIXTURES_DIR))
    assert result["type"] == "error"
    assert "error" in result
