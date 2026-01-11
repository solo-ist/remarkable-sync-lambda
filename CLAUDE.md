# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AWS Lambda OCR service for reMarkable tablet notebooks. Receives .rm page files from the Prose desktop app, extracts text (typed or handwritten), and returns formatted markdown. The Prose app handles reMarkable Cloud auth and downloads via rmapi-js; this Lambda focuses solely on OCR.

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
5. Send PNG to Claude Vision API for OCR
6. Return JSON response with markdown and confidence scores

Key components:
- `src/handler.py` — Lambda entry point, handles POST /ocr, coordinates the pipeline
- `src/rm_renderer.py` — Parse .rm v6 files, render strokes to PNG, extract typed text
- `src/claude_client.py` — Claude Vision API for handwriting OCR
- `src/markdown_formatter.py` — Format typed text output
- `src/secrets.py` — Lambda auth key from Secrets Manager
- `terraform/` — Infrastructure as code

### BYOK (Bring Your Own Key) Model

Users provide their own Anthropic API key via `x-anthropic-key` header for handwriting OCR. This shifts billing to users and avoids managing Anthropic credentials server-side. Keys are passed through but never stored or logged.

Pages with only typed text (no handwriting) don't require an Anthropic key since rmscene extracts text directly from .rm files.

### Content Detection

The `_filter_non_text_response()` function in `claude_client.py` catches cases where Claude describes images instead of extracting text (e.g., "I can see a drawing..."). It returns empty string when these patterns are detected.

## Request Limits

- Max 20 pages per request (`MAX_PAGES`)
- Max 5MB per page (`MAX_PAGE_SIZE`)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_KEY_SECRET_ARN` | ARN of Secrets Manager secret containing Lambda auth key |
| `API_KEY` | (Local testing) Override Lambda auth key |

## Development Notes

- Pure Python dependencies (rmscene, Pillow, anthropic) — no native libraries needed
- rmscene supports .rm v6 format (reMarkable firmware 3.x)
- Typed text extracted directly from .rm files (firmware v3.3+)
- reMarkable uses center-origin X coordinates; `rm_renderer.py` applies `X_OFFSET = 702` to convert
