"""Lambda handler for reMarkable notebook sync."""

import json
import logging
import os
from datetime import datetime, timezone

from rmapi_client import RmapiClient
from textract_client import TextractClient
from markdown_formatter import format_notebook_to_markdown

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients outside handler for connection reuse across invocations
rmapi = RmapiClient()
textract = TextractClient()


def lambda_handler(event: dict, context) -> dict:
    """
    Main Lambda entry point.

    Expects POST requests with x-api-key header for authentication.
    Returns synced notebooks as markdown.
    """
    try:
        # Validate API key
        headers = event.get("headers", {})
        api_key = headers.get("x-api-key") or headers.get("X-Api-Key")

        if not _validate_api_key(api_key):
            return _error_response(401, "Invalid or missing API key")

        # Parse request
        http_method = event.get("requestContext", {}).get("http", {}).get("method", "GET")

        if http_method != "POST":
            return _error_response(405, f"Method {http_method} not allowed. Use POST.")

        # Sync notebooks
        logger.info("Starting notebook sync")

        # Get list of notebooks from reMarkable Cloud
        notebooks = rmapi.list_notebooks()
        logger.info(f"Found {len(notebooks)} notebooks")

        synced_files = []

        for notebook in notebooks:
            try:
                # Download notebook pages as images
                pages = rmapi.download_notebook(notebook["id"])

                # OCR each page
                ocr_results = []
                for page_data in pages:
                    text = textract.detect_text(page_data)
                    ocr_results.append(text)

                # Format as markdown
                markdown_content = format_notebook_to_markdown(
                    title=notebook["name"],
                    pages=ocr_results,
                    synced_at=datetime.now(timezone.utc)
                )

                synced_files.append({
                    "path": f"{notebook['path']}/{notebook['name']}.md",
                    "content": markdown_content,
                    "pages": len(pages)
                })

            except Exception as e:
                logger.error(f"Failed to sync notebook {notebook['name']}: {e}")
                continue

        response_body = {
            "syncedAt": datetime.now(timezone.utc).isoformat(),
            "files": synced_files
        }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response_body)
        }

    except Exception as e:
        logger.exception("Unexpected error during sync")
        return _error_response(500, str(e))


def _validate_api_key(provided_key: str | None) -> bool:
    """Validate the provided API key against stored secret."""
    if not provided_key:
        return False

    import boto3

    secret_arn = os.environ.get("API_KEY_SECRET_ARN")
    if not secret_arn:
        # Fallback: check environment variable directly (for local testing)
        expected_key = os.environ.get("API_KEY")
        return provided_key == expected_key if expected_key else False

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    expected_key = response["SecretString"]

    return provided_key == expected_key


def _error_response(status_code: int, message: str) -> dict:
    """Create a standardized error response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message})
    }
