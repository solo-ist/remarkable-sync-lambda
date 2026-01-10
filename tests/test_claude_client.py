"""Tests for Claude Vision API client."""

import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, "src")

from claude_client import extract_text_from_image


def test_extract_text_returns_tuple():
    """Extract text returns (text, confidence) tuple."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Hello world")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("claude_client.anthropic.Anthropic", return_value=mock_client), \
         patch("claude_client.get_anthropic_api_key", return_value="test-key"):

        text, confidence = extract_text_from_image(b"fake-png-data")

        assert text == "Hello world"
        assert confidence == 1.0


def test_extract_text_sends_image():
    """Extract text sends base64 encoded image to Claude."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Extracted")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("claude_client.anthropic.Anthropic", return_value=mock_client), \
         patch("claude_client.get_anthropic_api_key", return_value="test-key"):

        extract_text_from_image(b"test-image-bytes")

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

    with patch("claude_client.anthropic.Anthropic", return_value=mock_client), \
         patch("claude_client.get_anthropic_api_key", return_value="test-key"):

        text, confidence = extract_text_from_image(b"blank-image")

        assert text == ""
        assert confidence == 1.0
