# reMarkable Sync Lambda

AWS Lambda service that syncs reMarkable tablet notebooks to markdown files via OCR.

## Overview

This service provides an HTTP endpoint that:
1. Connects to reMarkable Cloud via [rmapi](https://github.com/juruen/rmapi)
2. Downloads notebook files (.rm format)
3. Converts handwriting to text using AWS Textract
4. Returns markdown-formatted content

## Architecture

```
Client (Prose app)
    │
    ▼
Lambda Function URL (HTTPS + API Key)
    │
    ├── rmapi binary (Go, compiled for Amazon Linux 2)
    │   └── Authenticates with reMarkable Cloud
    │
    ├── AWS Textract
    │   └── OCR for handwriting recognition
    │
    └── AWS Secrets Manager
        └── Stores rmapi auth tokens
```

## API

### POST /sync

Syncs all notebooks and returns markdown content.

**Headers:**
- `x-api-key`: Required API key for authentication

**Response:**
```json
{
  "syncedAt": "2025-01-01T12:00:00Z",
  "files": [
    {
      "path": "Meetings/2025-01-15 Standup.md",
      "content": "---\nsource: remarkable\nsynced: 2025-01-01T12:00:00Z\n---\n\n# Content...",
      "pages": 3
    }
  ]
}
```

## Deployment

Infrastructure managed with Terraform. See `terraform/` directory.

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Local invoke (requires SAM CLI)
sam local invoke
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `RMAPI_CONFIG_SECRET_ARN` | ARN of Secrets Manager secret containing rmapi config |

## Related

- [Prose](https://github.com/solo-ist/prose) - Writing app that consumes this API
- [rmapi](https://github.com/juruen/rmapi) - reMarkable Cloud API client
