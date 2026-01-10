"""Render reMarkable .rm files to PNG images using rmscene + Pillow.

This module parses .rm v6 files and renders strokes to PNG for OCR processing.
It also extracts typed text directly when available (firmware v3.3+).
"""

from io import BytesIO
from PIL import Image, ImageDraw
from rmscene import read_blocks
from rmscene.scene_items import Line, Text

# reMarkable page dimensions in pixels
RM_WIDTH = 1404
RM_HEIGHT = 1872

# Coordinate system offset (reMarkable uses center origin for X)
X_OFFSET = RM_WIDTH / 2  # 702

# Brush colors (reMarkable uses 0=black, 1=gray, 2=white)
BRUSH_COLORS = {
    0: "black",
    1: "#808080",  # gray
    2: "white",
}


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


def render_rm_to_png(rm_bytes: bytes) -> bytes:
    """Render .rm strokes to PNG image.

    Parses the .rm binary format using rmscene and draws strokes
    using Pillow's ImageDraw. Handles stroke attributes like
    position, width, and color.

    Args:
        rm_bytes: Raw bytes of a .rm file

    Returns:
        PNG image as bytes
    """
    # Parse .rm file
    blocks = list(read_blocks(BytesIO(rm_bytes)))

    # Create blank white image
    img = Image.new("RGB", (RM_WIDTH, RM_HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    # Draw each stroke
    for block in blocks:
        line = None

        # rmscene v6 format: SceneLineItemBlock → item.value → Line
        if hasattr(block, "item") and block.item is not None:
            item = block.item
            if hasattr(item, "value") and item.value is not None:
                line = item.value

        # Fallback: direct line attribute
        elif hasattr(block, "value") and hasattr(block.value, "points"):
            line = block.value

        if line is None or not hasattr(line, "points"):
            continue

        if len(line.points) < 2:
            continue

        # Extract points (apply X offset for center-origin coordinate system)
        points = [(p.x + X_OFFSET, p.y) for p in line.points]

        # Determine stroke color
        color_idx = getattr(line, "color", 0)
        color = BRUSH_COLORS.get(color_idx, "black")

        # Determine stroke width (use thickness_scale or default)
        width = max(1, int(getattr(line, "thickness_scale", 2)))

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
        for block in blocks:
            # rmscene v6 format: SceneLineItemBlock → item.value → Line
            if hasattr(block, "item") and block.item is not None:
                item = block.item
                if hasattr(item, "value") and item.value is not None:
                    if hasattr(item.value, "points") and len(item.value.points) > 0:
                        return True
            # Fallback
            if hasattr(block, "value") and hasattr(block.value, "points"):
                if len(block.value.points) > 0:
                    return True
        return False
    except Exception:
        return False
