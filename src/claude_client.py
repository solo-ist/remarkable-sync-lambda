"""Claude Vision API client for OCR.

Uses Claude's vision capabilities to extract text from rendered
reMarkable page images with better handwriting recognition than
traditional OCR services.
"""

import base64
import logging

import anthropic

from secrets import get_anthropic_api_key

logger = logging.getLogger(__name__)

# Claude model for vision tasks - Sonnet balances cost and quality
MODEL = "claude-sonnet-4-20250514"

EXTRACTION_PROMPT = """Extract all handwritten and typed text from this image.

Return only the extracted text as clean markdown, preserving the document structure:
- Use headings (##) only if the text clearly indicates section titles
- Preserve lists (-, *, 1.) if present
- Separate paragraphs with blank lines

Do not include any explanations, commentary, or descriptions of the image.
If the image is blank or contains no readable text, return an empty string."""


def extract_text_from_image(png_bytes: bytes) -> tuple[str, float]:
    """Extract text from PNG using Claude Vision API.

    Args:
        png_bytes: PNG image data as bytes

    Returns:
        tuple of (markdown_text, confidence)
        Confidence is always 1.0 since Claude doesn't provide per-line scores
    """
    client = anthropic.Anthropic(api_key=get_anthropic_api_key())

    base64_image = base64.b64encode(png_bytes).decode("utf-8")

    logger.info(f"Sending image to Claude ({len(png_bytes)} bytes)")

    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": base64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": EXTRACTION_PROMPT,
                    },
                ],
            }
        ],
    )

    extracted_text = message.content[0].text
    logger.info(f"Extracted {len(extracted_text)} characters")

    return extracted_text, 1.0
