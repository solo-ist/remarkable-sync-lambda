"""Integration tests for process_page function.

Tests the core OCR pipeline that:
1. Decodes base64 .rm data
2. Extracts typed text directly
3. Renders handwriting to PNG and calls Claude OCR
4. Combines results into markdown
"""

import base64
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, "src")

from handler import process_page


class TestProcessPageTypedTextOnly:
    """Tests for pages with only typed text (no handwriting)."""

    def test_typed_text_returns_formatted_markdown(self):
        """Typed text is extracted and formatted without calling Claude."""
        rm_data = base64.b64encode(b"fake rm data").decode()

        with patch("handler.extract_typed_text", return_value="Hello World"), \
             patch("handler.has_strokes", return_value=False), \
             patch("handler.extract_text_from_image") as mock_claude:

            result = process_page("page-1", rm_data, anthropic_key=None)

            # Should not call Claude for typed-only pages
            mock_claude.assert_not_called()

            assert result["id"] == "page-1"
            assert "Hello World" in result["markdown"]
            assert result["confidence"] == 1.0

    def test_typed_text_no_anthropic_key_required(self):
        """Typed-only pages work without Anthropic key."""
        rm_data = base64.b64encode(b"fake rm data").decode()

        with patch("handler.extract_typed_text", return_value="Test content"), \
             patch("handler.has_strokes", return_value=False):

            # Should not raise even without anthropic_key
            result = process_page("page-1", rm_data, anthropic_key=None)
            assert result["markdown"] == "Test content"


class TestProcessPageHandwriting:
    """Tests for pages with handwriting (requires Claude OCR)."""

    def test_handwriting_calls_claude_ocr(self):
        """Handwriting pages render to PNG and call Claude."""
        rm_data = base64.b64encode(b"fake rm data").decode()
        mock_png = b"\x89PNG\r\n\x1a\nfake png data"

        with patch("handler.extract_typed_text", return_value=None), \
             patch("handler.has_strokes", return_value=True), \
             patch("handler.render_rm_to_png", return_value=mock_png) as mock_render, \
             patch("handler.extract_text_from_image", return_value=("Handwritten text", 0.92)) as mock_claude:

            result = process_page("page-1", rm_data, anthropic_key="sk-test-key")

            mock_render.assert_called_once()
            mock_claude.assert_called_once_with(mock_png, "sk-test-key")

            assert result["id"] == "page-1"
            assert result["markdown"] == "Handwritten text"
            assert result["confidence"] == 0.92

    def test_handwriting_without_key_raises_error(self):
        """Handwriting pages require Anthropic key."""
        rm_data = base64.b64encode(b"fake rm data").decode()

        with patch("handler.extract_typed_text", return_value=None), \
             patch("handler.has_strokes", return_value=True):

            try:
                process_page("page-1", rm_data, anthropic_key=None)
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "Anthropic API key required" in str(e)

    def test_handwriting_empty_ocr_result(self):
        """Empty OCR result still returns valid response."""
        rm_data = base64.b64encode(b"fake rm data").decode()

        with patch("handler.extract_typed_text", return_value=None), \
             patch("handler.has_strokes", return_value=True), \
             patch("handler.render_rm_to_png", return_value=b"png"), \
             patch("handler.extract_text_from_image", return_value=("", 0.5)):

            result = process_page("page-1", rm_data, anthropic_key="sk-test")

            assert result["markdown"] == ""
            assert result["confidence"] == 0.5


class TestProcessPageMixedContent:
    """Tests for pages with both typed text and handwriting."""

    def test_mixed_content_combines_results(self):
        """Pages with both typed and handwriting combine both."""
        rm_data = base64.b64encode(b"fake rm data").decode()

        with patch("handler.extract_typed_text", return_value="Typed header"), \
             patch("handler.has_strokes", return_value=True), \
             patch("handler.render_rm_to_png", return_value=b"png"), \
             patch("handler.extract_text_from_image", return_value=("Handwritten notes", 0.88)):

            result = process_page("page-1", rm_data, anthropic_key="sk-test")

            # Both should be present, separated by double newline
            assert "Typed header" in result["markdown"]
            assert "Handwritten notes" in result["markdown"]
            # Confidence reflects handwriting (lower confidence)
            assert result["confidence"] == 0.88

    def test_mixed_content_order(self):
        """Typed text appears before handwriting in output."""
        rm_data = base64.b64encode(b"fake rm data").decode()

        with patch("handler.extract_typed_text", return_value="FIRST"), \
             patch("handler.has_strokes", return_value=True), \
             patch("handler.render_rm_to_png", return_value=b"png"), \
             patch("handler.extract_text_from_image", return_value=("SECOND", 0.9)):

            result = process_page("page-1", rm_data, anthropic_key="sk-test")

            # Typed text should come before handwriting
            assert result["markdown"].index("FIRST") < result["markdown"].index("SECOND")


class TestProcessPageEmptyPage:
    """Tests for empty pages."""

    def test_empty_page_returns_empty_markdown(self):
        """Page with no content returns empty markdown."""
        rm_data = base64.b64encode(b"fake rm data").decode()

        with patch("handler.extract_typed_text", return_value=None), \
             patch("handler.has_strokes", return_value=False):

            result = process_page("page-1", rm_data, anthropic_key=None)

            assert result["id"] == "page-1"
            assert result["markdown"] == ""
            assert result["confidence"] == 1.0
