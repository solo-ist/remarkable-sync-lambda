"""Lambda handler for reMarkable OCR service.

Receives .rm files as base64-encoded data, extracts text (typed or handwritten),
and returns formatted markdown.
"""

import base64
import json
import logging
from hmac import compare_digest
from typing import Any

# Request limits to prevent DoS
MAX_PAGES = 20
MAX_PAGE_SIZE = 5 * 1024 * 1024  # 5MB per page

from secrets import get_api_key
from rm_renderer import extract_typed_text, render_rm_to_png, has_strokes
from textract_client import extract_text
from markdown_formatter import format_as_markdown, format_typed_text

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: dict, context: Any) -> dict:
    """Lambda entry point for OCR requests.

    Expected request format:
    {
        "pages": [
            {"id": "page-uuid", "data": "<base64 .rm data>"},
            ...
        ]
    }

    Response format:
    {
        "pages": [
            {"id": "page-uuid", "markdown": "...", "confidence": 0.92},
            ...
        ]
    }
    """
    try:
        # Validate API key
        provided_key = (
            event.get("headers", {}).get("x-api-key")
            or event.get("headers", {}).get("X-Api-Key")
        )
        expected_key = get_api_key()

        if not provided_key or not compare_digest(provided_key, expected_key):
            return error_response(401, "Invalid or missing API key")

        # Check HTTP method
        method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
        if method != "POST":
            return error_response(405, f"Method {method} not allowed. Use POST.")

        # Parse request body
        body = event.get("body", "")
        if event.get("isBase64Encoded", False):
            body = base64.b64decode(body).decode("utf-8")

        try:
            request_data = json.loads(body) if body else {}
        except json.JSONDecodeError as e:
            return error_response(400, f"Invalid JSON: {e}")

        pages = request_data.get("pages", [])
        if not pages:
            return error_response(400, "No pages provided")

        if len(pages) > MAX_PAGES:
            return error_response(400, f"Too many pages (max {MAX_PAGES})")

        logger.info(f"Processing {len(pages)} pages")

        # Process each page
        results = []
        failed_pages = []

        for page in pages:
            page_id = page.get("id", "unknown")
            page_data = page.get("data", "")

            if not page_data:
                failed_pages.append(page_id)
                continue

            if len(page_data) > MAX_PAGE_SIZE:
                logger.warning(f"Page {page_id} exceeds size limit")
                failed_pages.append(page_id)
                continue

            try:
                result = process_page(page_id, page_data)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing page {page_id}: {e}")
                failed_pages.append(page_id)

        response_body = {"pages": results}
        if failed_pages:
            response_body["failedPages"] = failed_pages

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response_body),
        }

    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        return error_response(500, "Internal server error")


def process_page(page_id: str, base64_data: str) -> dict:
    """Process a single page through the OCR pipeline.

    1. Decode base64 .rm data
    2. Try to extract typed text directly
    3. If handwriting present, render to PNG and OCR
    4. Format as markdown
    """
    # Decode .rm data
    rm_bytes = base64.b64decode(base64_data)

    # Try typed text extraction first (no OCR needed)
    typed_text = extract_typed_text(rm_bytes)
    has_handwriting = has_strokes(rm_bytes)

    markdown_parts = []
    confidence = 1.0  # Default confidence for typed text

    # Add typed text if present
    if typed_text:
        markdown_parts.append(format_typed_text(typed_text))
        logger.info(f"Page {page_id}: Extracted typed text directly")

    # Process handwriting if present
    if has_handwriting:
        logger.info(f"Page {page_id}: Rendering strokes for OCR")
        png_bytes = render_rm_to_png(rm_bytes)

        text_blocks, avg_confidence = extract_text(png_bytes)
        if text_blocks:
            handwriting_md = format_as_markdown(text_blocks)
            markdown_parts.append(handwriting_md)
            confidence = avg_confidence / 100.0  # Normalize to 0-1

    # Combine results
    markdown = "\n\n".join(filter(None, markdown_parts))

    return {
        "id": page_id,
        "markdown": markdown,
        "confidence": round(confidence, 2),
    }


def error_response(status_code: int, message: str) -> dict:
    """Create an error response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }
