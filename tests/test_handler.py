"""Tests for Lambda handler."""

import base64
import json
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, "src")

from handler import handler, process_page, error_response


def test_error_response():
    """Error response has correct structure."""
    result = error_response(400, "Bad request")
    assert result["statusCode"] == 400
    assert "application/json" in result["headers"]["Content-Type"]
    body = json.loads(result["body"])
    assert body["error"] == "Bad request"


def test_error_response_with_code():
    """Error response includes code when provided."""
    result = error_response(400, "Missing key", "MISSING_ANTHROPIC_KEY")
    body = json.loads(result["body"])
    assert body["error"] == "Missing key"
    assert body["code"] == "MISSING_ANTHROPIC_KEY"


def test_missing_api_key():
    """Request without API key returns 401."""
    with patch("handler.get_api_keys", return_value=["test-key"]):
        event = {
            "headers": {},
            "requestContext": {"http": {"method": "POST"}},
        }
        result = handler(event, None)
        assert result["statusCode"] == 401


def test_invalid_api_key():
    """Request with wrong API key returns 401."""
    with patch("handler.get_api_keys", return_value=["correct-key"]):
        event = {
            "headers": {"x-api-key": "wrong-key"},
            "requestContext": {"http": {"method": "POST"}},
        }
        result = handler(event, None)
        assert result["statusCode"] == 401


def test_grace_period_key_accepted():
    """During rotation, old (grace-period) key is still accepted and logged."""
    with patch("handler.get_api_keys", return_value=["new-key", "old-key"]), \
         patch("handler.process_page", return_value={"id": "t", "markdown": "", "confidence": 1.0}), \
         patch("handler.logger") as mock_logger:

        event = {
            "headers": {"x-api-key": "old-key"},
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({"pages": [{"id": "t", "data": base64.b64encode(b"x").decode()}]}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 200
        mock_logger.info.assert_any_call("Authenticated with grace-period key (rotation pending)")


def test_primary_key_accepted_during_rotation():
    """During rotation, new (primary) key is accepted."""
    with patch("handler.get_api_keys", return_value=["new-key", "old-key"]), \
         patch("handler.process_page", return_value={"id": "t", "markdown": "", "confidence": 1.0}):

        event = {
            "headers": {"x-api-key": "new-key"},
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({"pages": [{"id": "t", "data": base64.b64encode(b"x").decode()}]}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 200


def test_wrong_method():
    """Non-POST request returns 405."""
    with patch("handler.get_api_keys", return_value=["test-key"]):
        event = {
            "headers": {"x-api-key": "test-key"},
            "requestContext": {"http": {"method": "GET"}},
        }
        result = handler(event, None)
        assert result["statusCode"] == 405


def test_no_pages():
    """Request with no pages returns 400."""
    with patch("handler.get_api_keys", return_value=["test-key"]):
        event = {
            "headers": {"x-api-key": "test-key"},
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({"pages": []}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 400


def test_valid_request_structure():
    """Valid request returns proper response structure."""
    with patch("handler.get_api_keys", return_value=["test-key"]), \
         patch("handler.process_page", return_value={"id": "test", "markdown": "Hello", "confidence": 0.95}):

        event = {
            "headers": {"x-api-key": "test-key"},
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({
                "pages": [{"id": "test", "data": base64.b64encode(b"test").decode()}]
            }),
        }
        result = handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "pages" in body
        assert len(body["pages"]) == 1


def test_base64_encoded_body():
    """Handler decodes base64-encoded body."""
    with patch("handler.get_api_keys", return_value=["test-key"]), \
         patch("handler.process_page", return_value={"id": "test", "markdown": "Hello", "confidence": 0.95}):

        body = json.dumps({
            "pages": [{"id": "test", "data": base64.b64encode(b"test").decode()}]
        })
        event = {
            "headers": {"x-api-key": "test-key"},
            "requestContext": {"http": {"method": "POST"}},
            "body": base64.b64encode(body.encode()).decode(),
            "isBase64Encoded": True,
        }
        result = handler(event, None)
        assert result["statusCode"] == 200


# --- Error handling edge cases ---

def test_invalid_json_body():
    """Invalid JSON returns 400 with parse error."""
    with patch("handler.get_api_keys", return_value=["test-key"]):
        event = {
            "headers": {"x-api-key": "test-key"},
            "requestContext": {"http": {"method": "POST"}},
            "body": "not valid json {{{",
        }
        result = handler(event, None)
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Invalid JSON" in body["error"]


def test_too_many_pages():
    """Request with too many pages returns 400."""
    with patch("handler.get_api_keys", return_value=["test-key"]):
        # Create 21 pages (exceeds MAX_PAGES=20)
        pages = [{"id": f"page-{i}", "data": "dGVzdA=="} for i in range(21)]
        event = {
            "headers": {"x-api-key": "test-key"},
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({"pages": pages}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Too many pages" in body["error"]


def test_page_exceeds_size_limit():
    """Oversized page is added to failedPages."""
    with patch("handler.get_api_keys", return_value=["test-key"]), \
         patch("handler.MAX_PAGE_SIZE", 10):  # Set tiny limit for test

        # Create page larger than limit
        large_data = base64.b64encode(b"x" * 100).decode()
        event = {
            "headers": {"x-api-key": "test-key"},
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({"pages": [{"id": "big-page", "data": large_data}]}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "big-page" in body.get("failedPages", [])


def test_empty_page_data():
    """Page with empty data is added to failedPages."""
    with patch("handler.get_api_keys", return_value=["test-key"]):
        event = {
            "headers": {"x-api-key": "test-key"},
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({"pages": [{"id": "empty-page", "data": ""}]}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "empty-page" in body.get("failedPages", [])


def test_missing_anthropic_key_for_handwriting():
    """Missing Anthropic key for handwriting returns specific error."""
    with patch("handler.get_api_keys", return_value=["test-key"]), \
         patch("handler.extract_typed_text", return_value=None), \
         patch("handler.has_strokes", return_value=True):

        event = {
            "headers": {"x-api-key": "test-key"},  # No x-anthropic-key
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({
                "pages": [{"id": "hw-page", "data": base64.b64encode(b"test").decode()}]
            }),
        }
        result = handler(event, None)
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["code"] == "MISSING_ANTHROPIC_KEY"
        assert "x-anthropic-key" in body["error"]


def test_process_page_exception_adds_to_failed():
    """Generic exception in process_page adds to failedPages."""
    with patch("handler.get_api_keys", return_value=["test-key"]), \
         patch("handler.process_page", side_effect=Exception("Unexpected error")):

        event = {
            "headers": {"x-api-key": "test-key"},
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({
                "pages": [{"id": "error-page", "data": base64.b64encode(b"test").decode()}]
            }),
        }
        result = handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "error-page" in body.get("failedPages", [])


# --- Parallel processing ---

def test_pages_processed_in_parallel():
    """Multiple pages execute concurrently rather than sequentially."""
    import threading
    import time

    barrier = threading.Barrier(3)

    def slow_page(page_id, page_data, anthropic_client):
        # All 3 workers must hit the barrier before any can proceed.
        # If processing were sequential, this would deadlock since only
        # the first worker would ever reach the barrier.
        barrier.wait(timeout=2.0)
        return {"id": page_id, "markdown": "ok", "confidence": 1.0}

    with patch("handler.get_api_keys", return_value=["test-key"]), \
         patch("handler.process_page", side_effect=slow_page):

        pages = [
            {"id": f"page-{i}", "data": base64.b64encode(b"x").decode()}
            for i in range(3)
        ]
        event = {
            "headers": {"x-api-key": "test-key"},
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({"pages": pages}),
        }
        start = time.monotonic()
        result = handler(event, None)
        elapsed = time.monotonic() - start

        assert result["statusCode"] == 200
        assert elapsed < 1.5, f"Pages did not run concurrently (took {elapsed:.2f}s)"
        body = json.loads(result["body"])
        assert len(body["pages"]) == 3


def test_anthropic_client_reused_across_pages():
    """One Anthropic client is created per request and shared across pages."""
    captured_clients = []

    def capture_client(page_id, page_data, anthropic_client):
        captured_clients.append(anthropic_client)
        return {"id": page_id, "markdown": "", "confidence": 1.0}

    with patch("handler.get_api_keys", return_value=["test-key"]), \
         patch("handler.anthropic.Anthropic") as mock_anthropic_ctor, \
         patch("handler.process_page", side_effect=capture_client):

        sentinel_client = MagicMock(name="sentinel")
        mock_anthropic_ctor.return_value = sentinel_client

        pages = [
            {"id": f"page-{i}", "data": base64.b64encode(b"x").decode()}
            for i in range(4)
        ]
        event = {
            "headers": {
                "x-api-key": "test-key",
                "x-anthropic-key": "sk-user-key",
            },
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({"pages": pages}),
        }
        handler(event, None)

        # Constructor called exactly once, with the user's key.
        mock_anthropic_ctor.assert_called_once_with(api_key="sk-user-key")
        # Every page received the same client instance.
        assert len(captured_clients) == 4
        assert all(c is sentinel_client for c in captured_clients)


def test_missing_anthropic_key_aborts_under_parallelism():
    """One page raising MISSING_ANTHROPIC_KEY aborts the whole batch with 400."""
    def selective_raise(page_id, page_data, anthropic_client):
        if page_id == "hw-1":
            raise ValueError("Anthropic API key required for handwriting OCR")
        return {"id": page_id, "markdown": "typed", "confidence": 1.0}

    with patch("handler.get_api_keys", return_value=["test-key"]), \
         patch("handler.process_page", side_effect=selective_raise):

        pages = [
            {"id": "typed-1", "data": base64.b64encode(b"x").decode()},
            {"id": "hw-1", "data": base64.b64encode(b"y").decode()},
            {"id": "typed-2", "data": base64.b64encode(b"z").decode()},
        ]
        event = {
            "headers": {"x-api-key": "test-key"},  # No x-anthropic-key
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({"pages": pages}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["code"] == "MISSING_ANTHROPIC_KEY"
