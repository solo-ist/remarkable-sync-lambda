"""AWS Textract client for OCR processing."""

import boto3

textract_client = None


def get_textract_client():
    """Lazy initialization of Textract client."""
    global textract_client
    if textract_client is None:
        textract_client = boto3.client("textract")
    return textract_client


def extract_text(png_bytes: bytes) -> tuple[list[dict], float]:
    """Extract text from PNG image using AWS Textract.

    Args:
        png_bytes: PNG image as bytes

    Returns:
        Tuple of (text_blocks, average_confidence)
        where text_blocks is a list of dicts with:
        - text: The extracted text
        - confidence: Confidence score (0-100)
        - geometry: Bounding box info for positioning
    """
    client = get_textract_client()

    response = client.detect_document_text(
        Document={"Bytes": png_bytes}
    )

    text_blocks = []
    total_confidence = 0.0
    line_count = 0

    for block in response.get("Blocks", []):
        if block["BlockType"] == "LINE":
            text_blocks.append({
                "text": block["Text"],
                "confidence": block["Confidence"],
                "geometry": block["Geometry"],
            })
            total_confidence += block["Confidence"]
            line_count += 1

    avg_confidence = total_confidence / line_count if line_count > 0 else 0.0

    return text_blocks, avg_confidence
