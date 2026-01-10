"""Tests for textract_client module."""

import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, "src")

from textract_client import extract_text, get_textract_client


def test_get_textract_client_singleton():
    """Client is reused across calls."""
    with patch("textract_client.boto3") as mock_boto:
        mock_client = MagicMock()
        mock_boto.client.return_value = mock_client

        # Reset global
        import textract_client
        textract_client.textract_client = None

        client1 = get_textract_client()
        client2 = get_textract_client()

        # Should only create client once
        assert mock_boto.client.call_count == 1
        assert client1 is client2


def test_extract_text_empty_response():
    """Returns empty list when no text found."""
    mock_client = MagicMock()
    mock_client.detect_document_text.return_value = {"Blocks": []}

    with patch("textract_client.get_textract_client", return_value=mock_client):
        blocks, confidence = extract_text(b"fake png")

        assert blocks == []
        assert confidence == 0.0


def test_extract_text_single_line():
    """Extracts single line correctly."""
    mock_client = MagicMock()
    mock_client.detect_document_text.return_value = {
        "Blocks": [
            {
                "BlockType": "LINE",
                "Text": "Hello world",
                "Confidence": 95.0,
                "Geometry": {"BoundingBox": {"Top": 0.1}},
            }
        ]
    }

    with patch("textract_client.get_textract_client", return_value=mock_client):
        blocks, confidence = extract_text(b"fake png")

        assert len(blocks) == 1
        assert blocks[0]["text"] == "Hello world"
        assert blocks[0]["confidence"] == 95.0
        assert confidence == 95.0


def test_extract_text_multiple_lines():
    """Calculates average confidence across lines."""
    mock_client = MagicMock()
    mock_client.detect_document_text.return_value = {
        "Blocks": [
            {
                "BlockType": "LINE",
                "Text": "Line one",
                "Confidence": 90.0,
                "Geometry": {"BoundingBox": {"Top": 0.1}},
            },
            {
                "BlockType": "LINE",
                "Text": "Line two",
                "Confidence": 80.0,
                "Geometry": {"BoundingBox": {"Top": 0.2}},
            },
        ]
    }

    with patch("textract_client.get_textract_client", return_value=mock_client):
        blocks, confidence = extract_text(b"fake png")

        assert len(blocks) == 2
        assert confidence == 85.0  # Average of 90 and 80


def test_extract_text_ignores_non_lines():
    """Only extracts LINE block types."""
    mock_client = MagicMock()
    mock_client.detect_document_text.return_value = {
        "Blocks": [
            {
                "BlockType": "PAGE",
                "Confidence": 100.0,
            },
            {
                "BlockType": "LINE",
                "Text": "Actual text",
                "Confidence": 95.0,
                "Geometry": {"BoundingBox": {"Top": 0.1}},
            },
            {
                "BlockType": "WORD",
                "Text": "word",
                "Confidence": 90.0,
            },
        ]
    }

    with patch("textract_client.get_textract_client", return_value=mock_client):
        blocks, confidence = extract_text(b"fake png")

        assert len(blocks) == 1
        assert blocks[0]["text"] == "Actual text"
