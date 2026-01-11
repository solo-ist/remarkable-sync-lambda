"""Claude Vision API client for OCR.

Uses Claude's vision capabilities to extract text from rendered
reMarkable page images with better handwriting recognition than
traditional OCR services.
"""

import base64
import logging

import anthropic

logger = logging.getLogger(__name__)

# Claude model for vision tasks - Sonnet balances cost and quality
MODEL = "claude-sonnet-4-20250514"

EXTRACTION_PROMPT = """Extract all handwritten and typed text from this image.

Rules:
- Return ONLY the extracted text as clean markdown
- Use headings (##) only if the text clearly indicates section titles
- Preserve lists (-, *, 1.) if present
- Separate paragraphs with blank lines

CRITICAL: Do NOT describe the image, drawings, shapes, or sketches.
Do NOT explain what you see. Do NOT say "I can see..." or similar.
If there is no readable text, respond with exactly: NO_TEXT_FOUND"""


# Patterns that indicate Claude returned a description instead of extracted text
NO_TEXT_INDICATORS = [
    "NO_TEXT_FOUND",
    "I can see",
    "I cannot make out",
    "appears to be",
    "no readable text",
    "no text content",
    "cannot extract",
    "unable to extract",
    "drawing or sketch",
    "there is no",
]


def extract_text_from_image(png_bytes: bytes, api_key: str) -> tuple[str, float]:
    """Extract text from PNG using Claude Vision API.

    Args:
        png_bytes: PNG image data as bytes
        api_key: User's Anthropic API key

    Returns:
        tuple of (markdown_text, confidence)
        Confidence is always 1.0 since Claude doesn't provide per-line scores
    """
    client = anthropic.Anthropic(api_key=api_key)

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

    # Filter out responses that describe the image instead of extracting text
    extracted_text = _filter_non_text_response(extracted_text)

    logger.info(f"Extracted {len(extracted_text)} characters")

    return extracted_text, 1.0


def _filter_non_text_response(text: str) -> str:
    """Return empty string if response indicates no text was found.

    Claude sometimes describes images instead of returning empty string.
    This catches those cases.
    """
    text_lower = text.lower()
    for indicator in NO_TEXT_INDICATORS:
        if indicator.lower() in text_lower:
            return ""
    return text
