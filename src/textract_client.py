"""Client for AWS Textract OCR."""

import logging

import boto3

logger = logging.getLogger(__name__)


class TextractClient:
    """Wrapper around AWS Textract for handwriting recognition."""

    def __init__(self):
        self._client = boto3.client("textract")

    def detect_text(self, image_bytes: bytes) -> str:
        """
        Detect text in an image using Textract.

        Args:
            image_bytes: PNG or JPEG image data

        Returns:
            Extracted text as a string
        """
        logger.info(f"Calling Textract for image ({len(image_bytes)} bytes)")

        response = self._client.detect_document_text(
            Document={"Bytes": image_bytes}
        )

        # Extract text blocks and reconstruct document
        lines = []

        for block in response.get("Blocks", []):
            if block["BlockType"] == "LINE":
                lines.append(block["Text"])

        text = "\n".join(lines)
        logger.info(f"Extracted {len(lines)} lines of text")

        return text

    def analyze_document(self, image_bytes: bytes) -> dict:
        """
        Analyze document structure (tables, forms) in addition to text.

        This is more expensive but provides richer structure.

        Args:
            image_bytes: PNG or JPEG image data

        Returns:
            Dict with 'text', 'tables', 'forms' keys
        """
        logger.info(f"Calling Textract AnalyzeDocument ({len(image_bytes)} bytes)")

        response = self._client.analyze_document(
            Document={"Bytes": image_bytes},
            FeatureTypes=["TABLES", "FORMS"]
        )

        result = {
            "text": [],
            "tables": [],
            "forms": []
        }

        for block in response.get("Blocks", []):
            if block["BlockType"] == "LINE":
                result["text"].append(block["Text"])
            elif block["BlockType"] == "TABLE":
                result["tables"].append(block)
            elif block["BlockType"] == "KEY_VALUE_SET":
                result["forms"].append(block)

        return result
