"""Format Textract OCR output as markdown.

Groups text blocks by vertical position and attempts to detect
structure like headings, lists, and paragraphs.
"""

from typing import TypedDict


class TextBlock(TypedDict):
    text: str
    confidence: float
    geometry: dict


def format_as_markdown(text_blocks: list[TextBlock]) -> str:
    """Convert Textract text blocks to formatted markdown.

    Groups text by vertical position, detects structure patterns,
    and formats as clean markdown.

    Args:
        text_blocks: List of text blocks from Textract with geometry info

    Returns:
        Formatted markdown string
    """
    if not text_blocks:
        return ""

    # Sort blocks by vertical position (top to bottom)
    sorted_blocks = sorted(
        text_blocks,
        key=lambda b: b["geometry"]["BoundingBox"]["Top"]
    )

    lines = []
    prev_bottom = 0.0

    for block in sorted_blocks:
        text = block["text"].strip()
        if not text:
            continue

        bbox = block["geometry"]["BoundingBox"]
        top = bbox["Top"]
        height = bbox["Height"]

        # Detect paragraph breaks (gap between lines)
        gap = top - prev_bottom
        if prev_bottom > 0 and gap > height * 1.5:
            lines.append("")  # Add blank line for paragraph break

        # Format the line based on detected patterns
        formatted = format_line(text, bbox)
        lines.append(formatted)

        prev_bottom = top + height

    return "\n".join(lines)


def format_line(text: str, bbox: dict) -> str:
    """Apply formatting to a single line based on patterns.

    Detects:
    - List items (starting with -, *, numbers)
    - Regular text (no automatic heading detection for handwriting)
    """
    # Detect list items
    if text.startswith(("- ", "* ", "• ")):
        return text

    # Detect numbered lists
    if len(text) > 2 and text[0].isdigit() and text[1] in ".)":
        return text

    # Return text as-is - don't try to guess headings from handwriting
    # Textract can't distinguish heading vs body text in handwriting
    return text


def format_typed_text(text: str) -> str:
    """Format directly extracted typed text as markdown.

    Typed text from rmscene may already have some structure,
    so we do minimal processing.
    """
    if not text:
        return ""

    lines = text.split("\n")
    formatted_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped:
            formatted_lines.append(stripped)
        else:
            formatted_lines.append("")

    return "\n".join(formatted_lines)
