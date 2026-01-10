# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AWS Lambda OCR service for reMarkable tablet notebooks. Receives .rm page files from the Prose desktop app, extracts text (typed or handwritten), and returns formatted markdown. The Prose app handles reMarkable Cloud auth and downloads via rmapi-js; this Lambda focuses solely on OCR.

See `docs/INCEPTION.md` for full project scope and architecture.

## Commands

```bash
# Install dependencies
pip install -r src/requirements.txt

# Run all tests
pytest

# Run single test file
pytest tests/test_handler.py -v

# Run single test
pytest tests/test_handler.py::test_valid_request_structure -v

# Test locally with a .rm file
API_KEY=test-key ./scripts/test-local.sh tests/fixtures/sample.rm

# Deploy Lambda code
./scripts/deploy.sh

# Deploy infrastructure
cd terraform && terraform init && terraform apply
```

## Architecture

The Lambda uses a Function URL with API key auth (no API Gateway). Processing flow:

1. Receive POST with base64-encoded .rm page data
2. Parse .rm file using rmscene library
3. Check for typed text → extract directly (no OCR needed)
4. For handwriting → render strokes to PNG with Pillow
5. Send PNG to Textract for OCR
6. Format results as markdown
7. Return JSON response with confidence scores

Key components:
- `src/handler.py` — Lambda entry point, handles POST /ocr
- `src/rm_renderer.py` — Parse .rm files, render strokes to PNG
- `src/textract_client.py` — AWS Textract integration
- `src/markdown_formatter.py` — Format OCR output as markdown
- `src/secrets.py` — API key from Secrets Manager
- `terraform/` — Infrastructure as code

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_KEY_SECRET_ARN` | ARN of Secrets Manager secret containing API key |
| `API_KEY` | (Local testing) Override API key |

## Development Notes

- Pure Python dependencies (rmscene, Pillow) — no native libraries needed
- rmscene supports .rm v6 format (reMarkable firmware 3.x)
- Typed text extracted directly from .rm files (firmware v3.3+)
- Handwritten content rendered to PNG then OCR'd via Textract
- Function URL requires `x-api-key` header for authentication
- Textract works best with clear handwriting; messy writing may produce poor results
