# reMarkable OCR Lambda

AWS Lambda service that converts reMarkable tablet notebook pages (.rm files) to markdown via OCR.

## Overview

This service provides an HTTP endpoint that:
1. Receives .rm page data (base64-encoded) from the Prose desktop app
2. Extracts typed text directly when available (firmware v3.3+)
3. Renders handwritten strokes to PNG using Pillow
4. Converts handwriting to text using Claude Vision API
5. Returns markdown-formatted content with confidence scores

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Prose Desktop                             │
│  [Sync Button] ──► rmapi-js ──► Download .rm ──► Store locally  │
│                                       │                          │
│                                       ▼                          │
│                              [When OCR needed]                   │
│                                       │                          │
└───────────────────────────────────────┼──────────────────────────┘
                                        │
                                        ▼
                    ┌───────────────────────────────────────┐
                    │     This Lambda (Python 3.11)         │
                    │  Receive .rm ──► Parse ──► Render     │
                    │              ──► OCR ──► Markdown     │
                    └───────────────────────────────────────┘
```

The Prose desktop app handles reMarkable Cloud authentication and notebook downloads via rmapi-js. This Lambda focuses solely on the OCR pipeline.

## API

### POST /ocr

Process .rm page files and return extracted text as markdown.

**Headers:**
- `x-api-key`: Required API key for authentication

**Request:**
```json
{
  "pages": [
    { "id": "page-uuid-1", "data": "<base64 .rm data>" },
    { "id": "page-uuid-2", "data": "<base64 .rm data>" }
  ]
}
```

**Response:**
```json
{
  "pages": [
    {
      "id": "page-uuid-1",
      "markdown": "# Meeting Notes\n\nDiscussed the Q1 roadmap...",
      "confidence": 0.92
    },
    {
      "id": "page-uuid-2",
      "markdown": "## Action Items\n\n- Review PR by Friday...",
      "confidence": 0.88
    }
  ]
}
```

**Error Response:**
```json
{
  "error": "Failed to process page",
  "failedPages": ["page-uuid-1"]
}
```

## Deployment

### Infrastructure (Terraform)

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### Deploy Lambda Code

```bash
./scripts/deploy.sh
```

## Local Development

```bash
# Install dependencies
pip install -r src/requirements.txt

# Run tests
pytest

# Run single test file
pytest tests/test_handler.py -v

# Test locally with a .rm file
API_KEY=test-key ./scripts/test-local.sh path/to/page.rm
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_KEY_SECRET_ARN` | ARN of Secrets Manager secret containing API key |
| `ANTHROPIC_API_KEY_SECRET_ARN` | ARN of Secrets Manager secret containing Anthropic API key |
| `API_KEY` | (Local only) API key for testing |
| `ANTHROPIC_API_KEY` | (Local only) Anthropic API key for testing |

## Dependencies

- **rmscene** - Parse .rm v6 files from reMarkable tablets
- **Pillow** - Render strokes to PNG images
- **anthropic** - Claude Vision API for OCR
- **boto3** - AWS SDK for Secrets Manager

## Related

- [Prose](https://github.com/solo-ist/prose) - Writing app that consumes this API
- [rmscene](https://github.com/ricklupton/rmscene) - reMarkable file format parser
