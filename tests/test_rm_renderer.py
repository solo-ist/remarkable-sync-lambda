"""Tests for rm_renderer module.

Note: Most tests require sample .rm files in tests/fixtures/.
These tests use mocked data for CI compatibility.
"""

import sys
from unittest.mock import patch, MagicMock
from io import BytesIO

sys.path.insert(0, "src")

from rm_renderer import (
    RM_WIDTH,
    RM_HEIGHT,
    BRUSH_COLORS,
    extract_typed_text,
    render_rm_to_png,
    has_strokes,
)


def test_constants():
    """Verify reMarkable dimensions are correct."""
    assert RM_WIDTH == 1404
    assert RM_HEIGHT == 1872


def test_brush_colors():
    """Verify brush color mapping."""
    assert BRUSH_COLORS[0] == "black"
    assert BRUSH_COLORS[1] == "#808080"
    assert BRUSH_COLORS[2] == "white"


def test_extract_typed_text_none():
    """Returns None when no typed text present."""
    # Mock rmscene to return empty blocks
    with patch("rm_renderer.read_blocks", return_value=[]):
        result = extract_typed_text(b"fake rm data")
        assert result is None


def test_extract_typed_text_error():
    """Returns None on parse error."""
    with patch("rm_renderer.read_blocks", side_effect=Exception("parse error")):
        result = extract_typed_text(b"invalid data")
        assert result is None


def test_has_strokes_empty():
    """Returns False when no strokes present."""
    with patch("rm_renderer.read_blocks", return_value=[]):
        result = has_strokes(b"fake rm data")
        assert result is False


def test_has_strokes_error():
    """Returns False on parse error."""
    with patch("rm_renderer.read_blocks", side_effect=Exception("parse error")):
        result = has_strokes(b"invalid data")
        assert result is False


def test_render_produces_png():
    """Render produces valid PNG bytes."""
    # Mock rmscene to return empty blocks (blank page)
    with patch("rm_renderer.read_blocks", return_value=[]):
        result = render_rm_to_png(b"fake rm data")

        # Check PNG magic bytes
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

        # Check it's a reasonable size (blank white image)
        assert len(result) > 1000  # PNG header + data


def test_render_with_strokes():
    """Render draws strokes when present."""
    # Create mock block with lines
    mock_point = MagicMock()
    mock_point.x = 100
    mock_point.y = 100

    mock_point2 = MagicMock()
    mock_point2.x = 200
    mock_point2.y = 200

    mock_line = MagicMock()
    mock_line.points = [mock_point, mock_point2]
    mock_line.color = 0
    mock_line.brush_size = 2

    mock_block = MagicMock()
    mock_block.lines = [mock_line]

    with patch("rm_renderer.read_blocks", return_value=[mock_block]):
        result = render_rm_to_png(b"fake rm data")

        # Should produce valid PNG
        assert result[:8] == b"\x89PNG\r\n\x1a\n"
