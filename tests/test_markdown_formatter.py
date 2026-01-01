"""Tests for markdown formatter."""

from datetime import datetime, timezone
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from markdown_formatter import format_notebook_to_markdown, _clean_ocr_text


def test_format_notebook_basic():
    """Test basic notebook formatting."""
    result = format_notebook_to_markdown(
        title="Test Notebook",
        pages=["Hello world", "Page two content"],
        synced_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    )

    assert "title: \"Test Notebook\"" in result
    assert "source: remarkable" in result
    assert "# Test Notebook" in result
    assert "## Page 1" in result
    assert "Hello world" in result
    assert "## Page 2" in result
    assert "Page two content" in result


def test_format_notebook_single_page():
    """Test single page notebook (no page headers)."""
    result = format_notebook_to_markdown(
        title="Single Page",
        pages=["Just one page"],
        synced_at=datetime(2025, 1, 1, tzinfo=timezone.utc)
    )

    # Single page shouldn't have "## Page 1" header
    assert "## Page 1" not in result
    assert "Just one page" in result


def test_clean_ocr_text_headings():
    """Test that ALL CAPS lines become headings."""
    result = _clean_ocr_text("MEETING NOTES\nSome content here")

    assert "### Meeting Notes" in result
    assert "Some content here" in result


def test_clean_ocr_text_empty():
    """Test empty text handling."""
    assert _clean_ocr_text("") == ""
    assert _clean_ocr_text("   ") == ""


def test_clean_ocr_preserves_paragraphs():
    """Test that blank lines are preserved as paragraph breaks."""
    result = _clean_ocr_text("First paragraph.\n\nSecond paragraph.")

    assert "First paragraph." in result
    assert "Second paragraph." in result
    assert "\n\n" in result or result.count("\n") >= 1
