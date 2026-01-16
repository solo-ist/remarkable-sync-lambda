"""Tests for Claude Vision API client."""

import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, "src")

from claude_client import (
    extract_text_from_image,
    describe_illustration,
    _parse_extraction_response,
    HAS_DRAWINGS_MARKER,
)


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


def test_parse_extraction_response_passes_real_text():
    """Parser preserves actual extracted text."""
    text, has_drawings = _parse_extraction_response("Hello world")
    assert text == "Hello world"
    assert has_drawings is False

    text, has_drawings = _parse_extraction_response("# My Notes\n- Item 1")
    assert text == "# My Notes\n- Item 1"
    assert has_drawings is False


def test_parse_extraction_response_catches_no_text_marker():
    """Parser catches the NO_TEXT_FOUND marker."""
    text, has_drawings = _parse_extraction_response("NO_TEXT_FOUND")
    assert text == ""
    assert has_drawings is False


def test_parse_extraction_response_detects_drawings():
    """Parser detects HAS_DRAWINGS marker."""
    text, has_drawings = _parse_extraction_response(f"NO_TEXT_FOUND\n{HAS_DRAWINGS_MARKER}")
    assert text == ""
    assert has_drawings is True


def test_parse_extraction_response_mixed_content():
    """Parser handles text with drawings marker."""
    text, has_drawings = _parse_extraction_response(f"# My Notes\n\nSome text here\n{HAS_DRAWINGS_MARKER}")
    assert text == "# My Notes\n\nSome text here"
    assert has_drawings is True


def test_parse_extraction_response_catches_descriptions():
    """Parser catches descriptive responses about images."""
    descriptions = [
        "I can see this appears to be a simple line drawing or sketch.",
        "I cannot make out any readable text in this image.",
        "This appears to be a drawing with some geometric shapes.",
        "There is no readable text in this image.",
        "The image contains no text content to extract.",
    ]
    for desc in descriptions:
        text, _ = _parse_extraction_response(desc)
        assert text == "", f"Should filter: {desc[:50]}..."


def test_describe_illustration_returns_string():
    """Describe illustration returns lowercase description."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Smiling Face")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("claude_client.anthropic.Anthropic", return_value=mock_client):
        result = describe_illustration(b"fake-png-data", "test-key")

        assert result == "smiling face"


def test_extract_text_with_drawings_adds_illustration_marker():
    """Extract text includes illustration marker when drawings detected."""
    # First call returns text extraction with drawings marker
    extraction_response = MagicMock()
    extraction_response.content = [MagicMock(text=f"NO_TEXT_FOUND\n{HAS_DRAWINGS_MARKER}")]

    # Second call returns illustration description
    description_response = MagicMock()
    description_response.content = [MagicMock(text="sad robot face")]

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [extraction_response, description_response]

    with patch("claude_client.anthropic.Anthropic", return_value=mock_client):
        text, confidence = extract_text_from_image(b"drawing-png", "test-key")

        assert "[illustration: sad robot face]" in text
        assert confidence == 1.0


def test_extract_text_mixed_content():
    """Extract text handles mixed text and drawings."""
    # First call returns text with drawings marker
    extraction_response = MagicMock()
    extraction_response.content = [MagicMock(text=f"# My Notes\n\nHere is a flowchart:\n{HAS_DRAWINGS_MARKER}")]

    # Second call returns illustration description
    description_response = MagicMock()
    description_response.content = [MagicMock(text="flowchart diagram")]

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [extraction_response, description_response]

    with patch("claude_client.anthropic.Anthropic", return_value=mock_client):
        text, confidence = extract_text_from_image(b"mixed-png", "test-key")

        # Should have both text and illustration marker
        assert "# My Notes" in text
        assert "[illustration: flowchart diagram]" in text
        assert confidence == 1.0
