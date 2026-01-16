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

CRITICAL: Do NOT describe drawings, shapes, or sketches in prose.
Do NOT explain what you see. Do NOT say "I can see..." or similar.

If the image contains drawings/diagrams/sketches (not just text), add this marker at the END of your response on its own line:
[HAS_DRAWINGS]

If there is no readable text at all, respond with exactly: NO_TEXT_FOUND
If there is no readable text but there ARE drawings, respond with exactly: NO_TEXT_FOUND
[HAS_DRAWINGS]"""

ILLUSTRATION_PROMPT = """Describe this drawing in 5 words or fewer.
Return ONLY the description, no punctuation or explanation.
Examples: "smiling face", "robot with antenna", "flowchart diagram", "house with tree"
"""

# Marker indicating the response contains drawing information
HAS_DRAWINGS_MARKER = "[HAS_DRAWINGS]"

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

    For pages with text: returns extracted markdown
    For pages with drawings: returns illustration marker [illustration: description]
    For mixed content: returns text followed by illustration marker

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

    raw_response = message.content[0].text

    # Parse response to get text and detect drawings
    extracted_text, has_drawings = _parse_extraction_response(raw_response)

    logger.info(
        f"Extracted {len(extracted_text)} characters, has_drawings={has_drawings}"
    )

    # If drawings detected, add illustration marker
    if has_drawings:
        description = describe_illustration(png_bytes, api_key)
        marker = f"[illustration: {description}]"
        if extracted_text:
            # Mixed content: text + illustration marker
            extracted_text = f"{extracted_text}\n\n{marker}"
        else:
            # Drawing only: just illustration marker
            extracted_text = marker

    return extracted_text, 1.0


def _parse_extraction_response(text: str) -> tuple[str, bool]:
    """Parse extraction response to get text and drawing detection.

    Returns:
        tuple of (cleaned_text, has_drawings)
        - cleaned_text: The extracted text with markers removed, or empty if no text
        - has_drawings: True if the response indicates drawings are present
    """
    has_drawings = HAS_DRAWINGS_MARKER in text

    # Remove the marker from the text
    cleaned_text = text.replace(HAS_DRAWINGS_MARKER, "").strip()

    # Check if response indicates no actual text content
    text_lower = cleaned_text.lower()
    for indicator in NO_TEXT_INDICATORS:
        if indicator.lower() in text_lower:
            return "", has_drawings

    return cleaned_text, has_drawings


def describe_illustration(png_bytes: bytes, api_key: str) -> str:
    """Generate brief description of drawing.

    Args:
        png_bytes: PNG image data as bytes
        api_key: User's Anthropic API key

    Returns:
        Short description string (5 words or fewer)
    """
    client = anthropic.Anthropic(api_key=api_key)
    base64_image = base64.b64encode(png_bytes).decode("utf-8")

    logger.info(f"Describing illustration from image ({len(png_bytes)} bytes)")

    message = client.messages.create(
        model=MODEL,
        max_tokens=50,
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
                        "text": ILLUSTRATION_PROMPT,
                    },
                ],
            }
        ],
    )

    description = message.content[0].text.strip().lower()
    logger.info(f"Illustration description: {description}")

    return description
