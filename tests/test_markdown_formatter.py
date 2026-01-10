"""Tests for markdown_formatter module."""

import sys
sys.path.insert(0, "src")

from markdown_formatter import format_as_markdown, format_line, format_typed_text


def test_format_empty_blocks():
    """Empty input returns empty string."""
    assert format_as_markdown([]) == ""


def test_format_single_line():
    """Single text block formats correctly."""
    blocks = [
        {
            "text": "Hello world",
            "confidence": 95.0,
            "geometry": {
                "BoundingBox": {"Top": 0.1, "Height": 0.02, "Width": 0.3}
            },
        }
    ]
    result = format_as_markdown(blocks)
    assert result == "Hello world"


def test_format_multiple_lines():
    """Multiple blocks are joined with newlines."""
    blocks = [
        {
            "text": "First line",
            "confidence": 95.0,
            "geometry": {
                "BoundingBox": {"Top": 0.1, "Height": 0.02, "Width": 0.3}
            },
        },
        {
            "text": "Second line",
            "confidence": 90.0,
            "geometry": {
                "BoundingBox": {"Top": 0.15, "Height": 0.02, "Width": 0.3}
            },
        },
    ]
    result = format_as_markdown(blocks)
    assert "First line" in result
    assert "Second line" in result


def test_format_paragraph_break():
    """Large vertical gaps create paragraph breaks."""
    blocks = [
        {
            "text": "First paragraph",
            "confidence": 95.0,
            "geometry": {
                "BoundingBox": {"Top": 0.1, "Height": 0.02, "Width": 0.3}
            },
        },
        {
            "text": "Second paragraph",
            "confidence": 90.0,
            "geometry": {
                "BoundingBox": {"Top": 0.2, "Height": 0.02, "Width": 0.3}  # Big gap
            },
        },
    ]
    result = format_as_markdown(blocks)
    # Should have a blank line between paragraphs
    assert "\n\n" in result


def test_format_list_items():
    """List items are preserved."""
    blocks = [
        {
            "text": "- First item",
            "confidence": 95.0,
            "geometry": {
                "BoundingBox": {"Top": 0.1, "Height": 0.02, "Width": 0.3}
            },
        },
        {
            "text": "- Second item",
            "confidence": 90.0,
            "geometry": {
                "BoundingBox": {"Top": 0.15, "Height": 0.02, "Width": 0.3}
            },
        },
    ]
    result = format_as_markdown(blocks)
    assert "- First item" in result
    assert "- Second item" in result


def test_format_typed_text():
    """Typed text extraction formats correctly."""
    text = "Line one\n\nLine two\n  Line three  "
    result = format_typed_text(text)
    assert "Line one" in result
    assert "Line two" in result
    assert "Line three" in result


def test_format_typed_text_empty():
    """Empty typed text returns empty string."""
    assert format_typed_text("") == ""
    assert format_typed_text(None) == ""
