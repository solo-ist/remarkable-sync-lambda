"""Format OCR results as markdown."""

from datetime import datetime


def format_notebook_to_markdown(
    title: str,
    pages: list[str],
    synced_at: datetime
) -> str:
    """
    Format notebook OCR results as markdown.

    Args:
        title: Notebook title
        pages: List of OCR text, one per page
        synced_at: Timestamp of sync

    Returns:
        Formatted markdown string
    """
    # Build frontmatter
    frontmatter = f"""---
title: "{title}"
source: remarkable
synced: {synced_at.isoformat()}
pages: {len(pages)}
---
"""

    # Build content
    content_parts = [frontmatter, f"# {title}", ""]

    for i, page_text in enumerate(pages, start=1):
        if len(pages) > 1:
            content_parts.append(f"## Page {i}")
            content_parts.append("")

        # Clean up and add page content
        cleaned_text = _clean_ocr_text(page_text)
        content_parts.append(cleaned_text)
        content_parts.append("")  # Blank line between pages

    return "\n".join(content_parts)


def _clean_ocr_text(text: str) -> str:
    """
    Clean up OCR text for better markdown output.

    - Normalize whitespace
    - Detect potential headings (ALL CAPS lines)
    - Preserve paragraph breaks
    """
    if not text:
        return ""

    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        line = line.strip()

        if not line:
            # Preserve paragraph breaks
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue

        # Detect potential headings (short ALL CAPS lines)
        if line.isupper() and len(line) < 50:
            line = f"### {line.title()}"

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def format_page_as_markdown(page_text: str, page_number: int) -> str:
    """
    Format a single page as markdown.

    Simpler version for when you just need one page.
    """
    cleaned = _clean_ocr_text(page_text)
    return f"## Page {page_number}\n\n{cleaned}"
