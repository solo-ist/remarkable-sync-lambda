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
    """Render draws strokes when present (v6 format)."""
    # Create mock block matching rmscene v6 format:
    # block.item.value.points, block.item.value.color, etc.
    mock_point1 = MagicMock()
    mock_point1.x = 100
    mock_point1.y = 100

    mock_point2 = MagicMock()
    mock_point2.x = 200
    mock_point2.y = 200

    mock_line = MagicMock()
    mock_line.points = [mock_point1, mock_point2]
    mock_line.color = 0
    mock_line.thickness_scale = 2

    # v6 structure: block.item.value = line
    mock_item = MagicMock()
    mock_item.value = mock_line

    mock_block = MagicMock()
    mock_block.item = mock_item

    with patch("rm_renderer.read_blocks", return_value=[mock_block]):
        result = render_rm_to_png(b"fake rm data")

        # Should produce valid PNG
        assert result[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_applies_x_offset():
    """Render applies X_OFFSET for center-origin coordinate system."""
    from rm_renderer import X_OFFSET

    # Create stroke at x=0 (center in reMarkable coords)
    mock_point1 = MagicMock()
    mock_point1.x = 0  # Center in reMarkable = X_OFFSET in image
    mock_point1.y = 100

    mock_point2 = MagicMock()
    mock_point2.x = 100
    mock_point2.y = 100

    mock_line = MagicMock()
    mock_line.points = [mock_point1, mock_point2]
    mock_line.color = 0
    mock_line.thickness_scale = 2

    mock_item = MagicMock()
    mock_item.value = mock_line
    mock_block = MagicMock()
    mock_block.item = mock_item

    with patch("rm_renderer.read_blocks", return_value=[mock_block]), \
         patch("rm_renderer.ImageDraw.Draw") as mock_draw_class:

        mock_draw = MagicMock()
        mock_draw_class.return_value = mock_draw

        render_rm_to_png(b"fake rm data")

        # Verify draw.line was called
        mock_draw.line.assert_called()
        call_args = mock_draw.line.call_args

        # First argument is points list
        points = call_args[0][0]

        # x=0 should become x=X_OFFSET (702)
        assert points[0][0] == X_OFFSET
        # x=100 should become x=X_OFFSET+100
        assert points[1][0] == X_OFFSET + 100


def test_render_color_mapping():
    """Render maps color indices to correct colors."""
    # Test each color
    for color_idx, expected_color in [(0, "black"), (1, "#808080"), (2, "white")]:
        mock_point1 = MagicMock(x=0, y=0)
        mock_point2 = MagicMock(x=100, y=100)

        mock_line = MagicMock()
        mock_line.points = [mock_point1, mock_point2]
        mock_line.color = color_idx
        mock_line.thickness_scale = 2

        mock_item = MagicMock()
        mock_item.value = mock_line
        mock_block = MagicMock()
        mock_block.item = mock_item

        with patch("rm_renderer.read_blocks", return_value=[mock_block]), \
             patch("rm_renderer.ImageDraw.Draw") as mock_draw_class:

            mock_draw = MagicMock()
            mock_draw_class.return_value = mock_draw

            render_rm_to_png(b"fake rm data")

            # Verify correct fill color was used
            call_kwargs = mock_draw.line.call_args[1]
            assert call_kwargs["fill"] == expected_color, f"Color {color_idx} should be {expected_color}"


def test_render_unknown_color_defaults_to_black():
    """Unknown color index defaults to black."""
    mock_point1 = MagicMock(x=0, y=0)
    mock_point2 = MagicMock(x=100, y=100)

    mock_line = MagicMock()
    mock_line.points = [mock_point1, mock_point2]
    mock_line.color = 99  # Unknown color
    mock_line.thickness_scale = 2

    mock_item = MagicMock()
    mock_item.value = mock_line
    mock_block = MagicMock()
    mock_block.item = mock_item

    with patch("rm_renderer.read_blocks", return_value=[mock_block]), \
         patch("rm_renderer.ImageDraw.Draw") as mock_draw_class:

        mock_draw = MagicMock()
        mock_draw_class.return_value = mock_draw

        render_rm_to_png(b"fake rm data")

        call_kwargs = mock_draw.line.call_args[1]
        assert call_kwargs["fill"] == "black"


def test_render_stroke_width():
    """Render uses thickness_scale for stroke width."""
    mock_point1 = MagicMock(x=0, y=0)
    mock_point2 = MagicMock(x=100, y=100)

    mock_line = MagicMock()
    mock_line.points = [mock_point1, mock_point2]
    mock_line.color = 0
    mock_line.thickness_scale = 5

    mock_item = MagicMock()
    mock_item.value = mock_line
    mock_block = MagicMock()
    mock_block.item = mock_item

    with patch("rm_renderer.read_blocks", return_value=[mock_block]), \
         patch("rm_renderer.ImageDraw.Draw") as mock_draw_class:

        mock_draw = MagicMock()
        mock_draw_class.return_value = mock_draw

        render_rm_to_png(b"fake rm data")

        call_kwargs = mock_draw.line.call_args[1]
        assert call_kwargs["width"] == 5


def test_render_stroke_width_minimum():
    """Stroke width has minimum of 1."""
    mock_point1 = MagicMock(x=0, y=0)
    mock_point2 = MagicMock(x=100, y=100)

    mock_line = MagicMock()
    mock_line.points = [mock_point1, mock_point2]
    mock_line.color = 0
    mock_line.thickness_scale = 0.5  # Less than 1

    mock_item = MagicMock()
    mock_item.value = mock_line
    mock_block = MagicMock()
    mock_block.item = mock_item

    with patch("rm_renderer.read_blocks", return_value=[mock_block]), \
         patch("rm_renderer.ImageDraw.Draw") as mock_draw_class:

        mock_draw = MagicMock()
        mock_draw_class.return_value = mock_draw

        render_rm_to_png(b"fake rm data")

        call_kwargs = mock_draw.line.call_args[1]
        assert call_kwargs["width"] >= 1


def test_render_skips_single_point_strokes():
    """Strokes with less than 2 points are skipped."""
    mock_point = MagicMock(x=0, y=0)

    mock_line = MagicMock()
    mock_line.points = [mock_point]  # Only 1 point
    mock_line.color = 0

    mock_item = MagicMock()
    mock_item.value = mock_line
    mock_block = MagicMock()
    mock_block.item = mock_item

    with patch("rm_renderer.read_blocks", return_value=[mock_block]), \
         patch("rm_renderer.ImageDraw.Draw") as mock_draw_class:

        mock_draw = MagicMock()
        mock_draw_class.return_value = mock_draw

        render_rm_to_png(b"fake rm data")

        # draw.line should not be called for single-point stroke
        mock_draw.line.assert_not_called()


def test_has_strokes_v6_format():
    """has_strokes detects strokes in v6 format."""
    mock_point = MagicMock(x=0, y=0)

    mock_line = MagicMock()
    mock_line.points = [mock_point]

    mock_item = MagicMock()
    mock_item.value = mock_line
    mock_block = MagicMock()
    mock_block.item = mock_item

    with patch("rm_renderer.read_blocks", return_value=[mock_block]):
        assert has_strokes(b"fake rm data") is True
