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


def test_missing_api_key():
    """Request without API key returns 401."""
    with patch("handler.get_api_key", return_value="test-key"):
        event = {
            "headers": {},
            "requestContext": {"http": {"method": "POST"}},
        }
        result = handler(event, None)
        assert result["statusCode"] == 401


def test_invalid_api_key():
    """Request with wrong API key returns 401."""
    with patch("handler.get_api_key", return_value="correct-key"):
        event = {
            "headers": {"x-api-key": "wrong-key"},
            "requestContext": {"http": {"method": "POST"}},
        }
        result = handler(event, None)
        assert result["statusCode"] == 401


def test_wrong_method():
    """Non-POST request returns 405."""
    with patch("handler.get_api_key", return_value="test-key"):
        event = {
            "headers": {"x-api-key": "test-key"},
            "requestContext": {"http": {"method": "GET"}},
        }
        result = handler(event, None)
        assert result["statusCode"] == 405


def test_no_pages():
    """Request with no pages returns 400."""
    with patch("handler.get_api_key", return_value="test-key"):
        event = {
            "headers": {"x-api-key": "test-key"},
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({"pages": []}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 400


def test_valid_request_structure():
    """Valid request returns proper response structure."""
    with patch("handler.get_api_key", return_value="test-key"), \
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
    with patch("handler.get_api_key", return_value="test-key"), \
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
