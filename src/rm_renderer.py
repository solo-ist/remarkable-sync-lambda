"""Render reMarkable .rm files to PNG images using rmscene + Pillow.

This module parses .rm v6 files and renders strokes to PNG for OCR processing.
It also extracts typed text directly when available (firmware v3.3+).
"""

from io import BytesIO
from PIL import Image, ImageDraw
from rmscene import read_blocks
from rmscene.scene_items import Line, Text

# reMarkable native page dimensions in pixels (do not change — these reflect
# the device coordinate system, not the rendered output size).
RM_WIDTH = 1404
RM_HEIGHT = 1872

# Coordinate system offset (reMarkable uses center origin for X)
X_OFFSET = RM_WIDTH / 2  # 702

# Output downscale factor. Halving each axis quarters the pixel count and,
# combined with grayscale (1 channel vs 3), drops payload size by ~85% for
# typical pages while remaining readable for Claude Vision OCR.
RENDER_SCALE = 0.5

# Cap on rendered canvas height in native pixels. ~6× standard page height,
# which covers the longest "infinite scroll" pages observed while keeping the
# largest dimension under Claude Vision's 8000² ceiling at scale=0.5.
MAX_CANVAS_HEIGHT = 12000

# Bottom/right padding around stroke extents so glyphs don't touch the edge.
PADDING_PX = 20

# Brush colors (reMarkable uses 0=black, 1=gray, 2=white). Color names and
# hex strings are accepted by PIL ImageDraw in both "RGB" and "L" modes.
BRUSH_COLORS = {
    0: "black",
    1: "#808080",  # gray
    2: "white",
}


def _iter_lines(blocks):
    """Yield Line objects from rmscene blocks (v6 format + legacy fallback)."""
    for block in blocks:
        if hasattr(block, "item") and block.item is not None:
            item = block.item
            if hasattr(item, "value") and item.value is not None:
                line = item.value
                if hasattr(line, "points"):
                    yield line
                    continue
        if hasattr(block, "value") and hasattr(block.value, "points"):
            yield block.value


def _compute_canvas_dims(blocks, scale):
    """Walk strokes once to derive a canvas that fits every point.

    Returns (width, height, x_offset_native) where width/height are the scaled
    output pixel dimensions and x_offset_native is the un-scaled X shift
    applied to each point so that center-origin reMarkable coords land inside
    the canvas. Floors at standard page dims so empty/short pages still render
    at the familiar size; ceilings at MAX_CANVAS_HEIGHT to bound payload.
    """
    max_y_strokes = 0
    max_x_extent = X_OFFSET  # half-width from center (RM_WIDTH / 2)
    for line in _iter_lines(blocks):
        for p in line.points:
            if p.y > max_y_strokes:
                max_y_strokes = p.y
            ax = abs(p.x)
            if ax > max_x_extent:
                max_x_extent = ax
    # Only pad past the standard page when strokes actually overflow it —
    # short/empty pages keep their familiar RM_HEIGHT so existing call sites
    # and the Prose UI see no dimension change for typical content.
    if max_y_strokes > RM_HEIGHT:
        max_y = min(max_y_strokes + PADDING_PX, MAX_CANVAS_HEIGHT)
    else:
        max_y = RM_HEIGHT
    width = max(1, int(max(RM_WIDTH, 2 * max_x_extent) * scale))
    height = max(1, int(max_y * scale))
    return width, height, max_x_extent


def extract_typed_text(rm_bytes: bytes) -> str | None:
    """Extract typed text directly from .rm file (firmware v3.3+).

    Returns the text content if the page contains typed text,
    or None if it only contains handwritten strokes.
    """
    try:
        blocks = list(read_blocks(BytesIO(rm_bytes)))
        text_parts = []

        for block in blocks:
            if isinstance(block, Text):
                if hasattr(block, "text") and block.text:
                    text_parts.append(block.text)

        if text_parts:
            return "\n".join(text_parts)
        return None
    except Exception:
        return None


def render_rm_to_png(rm_bytes: bytes, scale: float = RENDER_SCALE) -> bytes:
    """Render .rm strokes to PNG image.

    Parses the .rm binary format using rmscene and draws strokes
    using Pillow's ImageDraw. Handles stroke attributes like
    position, width, and color.

    Args:
        rm_bytes: Raw bytes of a .rm file
        scale: Output downscale factor (1.0 = native, 0.5 = half-size).
            Affects canvas dimensions, X_OFFSET application, and stroke widths
            uniformly so spatial relationships are preserved.

    Returns:
        PNG image as bytes (8-bit grayscale)
    """
    # Parse .rm file
    blocks = list(read_blocks(BytesIO(rm_bytes)))

    # Size the canvas to the strokes' actual extent so infinite-scroll pages
    # aren't truncated. x_offset_native is the un-scaled X shift; using
    # max(X_OFFSET, ...) keeps the center-origin transform valid even when a
    # stroke pushes past the standard half-width.
    out_w, out_h, x_offset_native = _compute_canvas_dims(blocks, scale)
    x_offset_effective = max(X_OFFSET, x_offset_native)

    # Grayscale ("L") mode is one byte per pixel vs three for "RGB" — direct
    # 3x payload reduction. Strokes are monochrome on white so no color is lost.
    img = Image.new("L", (out_w, out_h), "white")
    draw = ImageDraw.Draw(img)

    # Draw each stroke
    for line in _iter_lines(blocks):
        if len(line.points) < 2:
            continue

        # Extract points: apply X offset for center-origin coordinate system,
        # then scale into output canvas.
        points = [((p.x + x_offset_effective) * scale, p.y * scale) for p in line.points]

        # Determine stroke color
        color_idx = getattr(line, "color", 0)
        color = BRUSH_COLORS.get(color_idx, "black")

        # Stroke width scales with canvas so visual line weight is preserved.
        # `thickness_scale` defaults to 2; `max(1, ...)` keeps hairlines visible
        # after scaling, especially at scale < 0.5.
        width = max(1, int(getattr(line, "thickness_scale", 2) * scale))

        # Draw the stroke
        if len(points) == 2:
            draw.line(points, fill=color, width=width)
        else:
            # Draw as connected line segments
            draw.line(points, fill=color, width=width, joint="curve")

    # Export to PNG bytes
    output = BytesIO()
    img.save(output, format="PNG", optimize=True)
    return output.getvalue()


def has_strokes(rm_bytes: bytes) -> bool:
    """Check if the .rm file contains any handwritten strokes.

    Used to determine if OCR is needed or if typed text extraction
    is sufficient.
    """
    try:
        blocks = list(read_blocks(BytesIO(rm_bytes)))
        return any(len(line.points) > 0 for line in _iter_lines(blocks))
    except Exception:
        return False
