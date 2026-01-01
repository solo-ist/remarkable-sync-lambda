# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AWS Lambda service that syncs reMarkable tablet notebooks to markdown via OCR. The Lambda downloads notebooks from reMarkable Cloud using rmapi, converts handwriting to text with AWS Textract, and returns structured markdown. The Prose desktop app polls this endpoint to sync notebooks locally.

See `docs/INCEPTION.md` for full project scope and architecture.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run single test file
pytest tests/test_handler.py

# Run single test
pytest tests/test_handler.py::test_sync_endpoint -v

# Local invoke with SAM CLI
sam local invoke

# Deploy infrastructure
cd terraform && terraform init && terraform apply

# Package Lambda for deployment
./scripts/package.sh
```

## Architecture

The Lambda uses a Function URL with API key auth (no API Gateway). Request flow:

1. Lambda reads rmapi config from Secrets Manager
2. rmapi binary (Go, compiled for Amazon Linux 2 x86_64) downloads .rm files from reMarkable Cloud
3. Files are converted to images and sent to Textract for OCR
4. Results are formatted as markdown and returned as JSON

Key components:
- `src/handler.py` — Lambda entry point, handles POST /sync
- `src/rmapi_client.py` — Wraps the rmapi binary subprocess
- `src/textract_client.py` — AWS Textract integration
- `src/markdown_formatter.py` — Formats OCR output as markdown
- `terraform/` — Infrastructure as code

## Environment Variables

| Variable | Description |
|----------|-------------|
| `RMAPI_CONFIG_SECRET_ARN` | ARN of Secrets Manager secret containing rmapi config |

## Development Notes

- rmapi binary must be compiled for Amazon Linux 2 (x86_64) - cannot use macOS binary
- rmapi tokens are long-lived; stored in Secrets Manager after initial local auth
- Function URL requires `x-api-key` header for authentication
- Textract works best with clear handwriting; messy writing may produce poor results
