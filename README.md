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
- `x-api-key`: Required API key for Lambda authentication
- `x-anthropic-key`: User's Anthropic API key (required for handwriting OCR)

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

**Error Responses:**
```json
{
  "error": "Failed to process page",
  "failedPages": ["page-uuid-1"]
}
```

```json
{
  "error": "Anthropic API key required for handwriting OCR. Provide x-anthropic-key header.",
  "code": "MISSING_ANTHROPIC_KEY"
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
| `API_KEY_SECRET_ARN` | ARN of Secrets Manager secret containing Lambda auth key |
| `API_KEY` | (Local only) Lambda auth key for testing |

Note: Anthropic API keys are now provided per-request via the `x-anthropic-key` header.

## Dependencies

- **rmscene** - Parse .rm v6 files from reMarkable tablets
- **Pillow** - Render strokes to PNG images
- **anthropic** - Claude Vision API for OCR
- **boto3** - AWS SDK for Secrets Manager

## Security

This Lambda uses a "bring your own API key" model for Claude Vision OCR:

- **Lambda auth key** (`x-api-key`): Shared key that authenticates requests to this Lambda
- **User's Anthropic key** (`x-anthropic-key`): User provides their own key for OCR billing

### Privacy Notes

- User API keys are passed through this Lambda to Anthropic but are **not stored or logged**
- All communication is encrypted via HTTPS
- Keys exist only in memory during request processing
- Users should understand their API key passes through this service

### For Typed Text

Pages with only typed text (no handwriting) are processed without calling Claude Vision, so no Anthropic key is required for those pages.

## Related

- [Prose](https://github.com/solo-ist/prose) - Writing app that consumes this API
- [rmscene](https://github.com/ricklupton/rmscene) - reMarkable file format parser
