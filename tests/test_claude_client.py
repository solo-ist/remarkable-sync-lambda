"""Tests for Claude Vision API client."""

import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, "src")

from claude_client import extract_text_from_image, _filter_non_text_response


def test_extract_text_returns_tuple():
    """Extract text returns (text, confidence) tuple."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Hello world")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("claude_client.anthropic.Anthropic", return_value=mock_client):
        text, confidence = extract_text_from_image(b"fake-png-data", "test-key")

        assert text == "Hello world"
        assert confidence == 1.0


def test_extract_text_sends_image():
    """Extract text sends base64 encoded image to Claude."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Extracted")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("claude_client.anthropic.Anthropic", return_value=mock_client):
        extract_text_from_image(b"test-image-bytes", "test-key")

        # Verify messages.create was called
        mock_client.messages.create.assert_called_once()

        # Check the call arguments
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["model"] == "claude-sonnet-4-20250514"
        assert call_args.kwargs["max_tokens"] == 4096

        # Check message content includes image
        messages = call_args.kwargs["messages"]
        assert len(messages) == 1
        content = messages[0]["content"]
        assert len(content) == 2
        assert content[0]["type"] == "image"
        assert content[1]["type"] == "text"


def test_extract_text_empty_result():
    """Extract text handles empty response."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("claude_client.anthropic.Anthropic", return_value=mock_client):
        text, confidence = extract_text_from_image(b"blank-image", "test-key")

        assert text == ""
        assert confidence == 1.0


def test_filter_non_text_response_passes_real_text():
    """Filter preserves actual extracted text."""
    assert _filter_non_text_response("Hello world") == "Hello world"
    assert _filter_non_text_response("# My Notes\n- Item 1") == "# My Notes\n- Item 1"


def test_filter_non_text_response_catches_no_text_marker():
    """Filter catches the NO_TEXT_FOUND marker."""
    assert _filter_non_text_response("NO_TEXT_FOUND") == ""


def test_filter_non_text_response_catches_descriptions():
    """Filter catches descriptive responses about images."""
    descriptions = [
        "I can see this appears to be a simple line drawing or sketch, but I cannot make out any clear handwritten or typed text in this image.",
        "I cannot make out any readable text in this image.",
        "This appears to be a drawing with some geometric shapes.",
        "There is no readable text in this image.",
        "The image contains no text content to extract.",
    ]
    for desc in descriptions:
        assert _filter_non_text_response(desc) == "", f"Should filter: {desc[:50]}..."
