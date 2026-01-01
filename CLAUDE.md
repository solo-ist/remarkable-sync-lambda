# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

AWS Lambda service that syncs reMarkable tablet notebooks to markdown via OCR.

See `docs/INCEPTION.md` for full project scope and architecture.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Deploy infrastructure
cd terraform && terraform apply

# Package Lambda
./scripts/package.sh
```

## Architecture

- **Lambda Function**: Python 3.11 runtime
- **rmapi**: Go binary for reMarkable Cloud API
- **Textract**: AWS service for OCR
- **Secrets Manager**: Stores rmapi credentials
- **Function URL**: HTTPS endpoint with API key auth

## Key Files

| File | Purpose |
|------|---------|
| `src/handler.py` | Lambda entry point |
| `src/rmapi_client.py` | rmapi binary wrapper |
| `src/textract_client.py` | AWS Textract integration |
| `terraform/*.tf` | Infrastructure as code |

## Development Notes

- rmapi binary must be compiled for Amazon Linux 2 (x86_64)
- Textract works best with clear handwriting
- Function URL requires `x-api-key` header for auth
