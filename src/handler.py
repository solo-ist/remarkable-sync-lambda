"""Lambda handler for reMarkable OCR service.

Receives .rm files as base64-encoded data, extracts text (typed or handwritten),
and returns formatted markdown.
"""

import base64
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from hmac import compare_digest
from typing import Any

import anthropic

# Request limits to prevent DoS
MAX_PAGES = 20
MAX_PAGE_SIZE = 5 * 1024 * 1024  # 5MB per page

from secrets import get_api_keys
from rm_renderer import extract_typed_text, render_rm_to_png, has_strokes
from claude_client import extract_text_from_image
from markdown_formatter import format_typed_text

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
        # Validate API key against all valid keys (supports dual-key rotation)
        provided_key = (
            event.get("headers", {}).get("x-api-key")
            or event.get("headers", {}).get("X-Api-Key")
        )
        valid_keys = get_api_keys()

        if not provided_key:
            return error_response(401, "Invalid or missing API key")

        key_index = next(
            (i for i, k in enumerate(valid_keys) if compare_digest(provided_key, k)),
            -1,
        )
        if key_index < 0:
            return error_response(401, "Invalid or missing API key")

        if key_index > 0:
            logger.info("Authenticated with grace-period key (rotation pending)")

        # Extract user's Anthropic API key and instantiate one client per
        # Lambda invocation. Reusing the client across pages amortizes
        # TLS handshake and HTTP connection-pool setup over the request.
        anthropic_key = (
            event.get("headers", {}).get("x-anthropic-key")
            or event.get("headers", {}).get("X-Anthropic-Key")
        )
        anthropic_client = (
            anthropic.Anthropic(api_key=anthropic_key) if anthropic_key else None
        )

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

        results = []
        failed_pages = []

        # Pre-validate cheap checks (missing data, size) before spawning threads
        # so we don't burn a worker just to short-circuit. Pages that pass
        # validation get submitted to the pool.
        valid_pages = []
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

            valid_pages.append((page_id, page_data))

        # Process pages in parallel. Prose batches at BATCH_SIZE=5 (ocr.ts:245)
        # so 5 workers matches the wire contract; oversizing wastes RAM with no
        # latency win since each worker is I/O-bound waiting on Claude.
        #
        # MISSING_ANTHROPIC_KEY policy: whole-batch abort with HTTP 400. Pages
        # in a batch share the same client/user, so a missing key fails every
        # handwriting page anyway. Cancelling pending futures avoids spending
        # any further Anthropic-side cost for typed-only pages we'd discard.
        missing_key_response: dict | None = None

        if valid_pages:
            with ThreadPoolExecutor(max_workers=min(5, len(valid_pages))) as executor:
                future_to_id = {
                    executor.submit(process_page, page_id, page_data, anthropic_client): page_id
                    for page_id, page_data in valid_pages
                }
                for future in as_completed(future_to_id):
                    page_id = future_to_id[future]
                    try:
                        results.append(future.result())
                    except ValueError as e:
                        if "Anthropic API key required" in str(e):
                            # Cancel any not-yet-started futures. In-flight
                            # Claude calls cannot be killed by concurrent.futures
                            # but the `with` block's shutdown will wait for them
                            # to drain.
                            for f in future_to_id:
                                f.cancel()
                            missing_key_response = error_response(
                                400,
                                "Anthropic API key required for handwriting OCR. "
                                "Provide x-anthropic-key header.",
                                "MISSING_ANTHROPIC_KEY",
                            )
                            break
                        logger.error(f"Error processing page {page_id}: {e}")
                        failed_pages.append(page_id)
                    except Exception as e:
                        logger.error(f"Error processing page {page_id}: {e}")
                        failed_pages.append(page_id)

        if missing_key_response is not None:
            return missing_key_response

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


def process_page(
    page_id: str,
    base64_data: str,
    anthropic_client: anthropic.Anthropic | None,
) -> dict:
    """Process a single page through the OCR pipeline.

    1. Decode base64 .rm data
    2. Try to extract typed text directly
    3. If handwriting present, render to PNG and OCR
    4. Format as markdown

    Args:
        page_id: Unique identifier for the page
        base64_data: Base64-encoded .rm file data
        anthropic_client: Anthropic client for OCR (required for handwriting;
            None is allowed for typed-only pages)
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
        if anthropic_client is None:
            raise ValueError("Anthropic API key required for handwriting OCR")

        logger.info(f"Page {page_id}: Rendering strokes for OCR")
        png_bytes = render_rm_to_png(rm_bytes)

        handwriting_md, confidence = extract_text_from_image(png_bytes, anthropic_client)
        if handwriting_md:
            markdown_parts.append(handwriting_md)

    # Combine results
    markdown = "\n\n".join(filter(None, markdown_parts))

    return {
        "id": page_id,
        "markdown": markdown,
        "confidence": round(confidence, 2),
    }


def error_response(status_code: int, message: str, code: str | None = None) -> dict:
    """Create an error response."""
    body = {"error": message}
    if code:
        body["code"] = code
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
