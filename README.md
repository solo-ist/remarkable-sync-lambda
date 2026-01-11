# reMarkable OCR Lambda

Convert reMarkable tablet notebooks to markdown via Claude Vision.

```
Prose Desktop                          This Lambda
┌────────────────────┐                ┌─────────────────────────┐
│  Sync Button       │                │  .rm ──► Parse          │
│       │            │   POST /ocr    │       ──► Render PNG    │
│       ▼            │ ─────────────► │       ──► Claude Vision │
│  rmapi-js          │                │       ──► Markdown      │
│  Download .rm      │ ◄───────────── │                         │
└────────────────────┘    JSON        └─────────────────────────┘
```

## How It Works

1. **Typed text** — Extracted directly from .rm files (firmware v3.3+), no OCR needed
2. **Handwriting** — Rendered to PNG, then OCR'd via Claude Vision API
3. **Mixed pages** — Both methods combined, returned as unified markdown

## API

### `POST /ocr`

**Headers**
| Header | Required | Description |
|--------|----------|-------------|
| `x-api-key` | Yes | Lambda authentication |
| `x-anthropic-key` | For handwriting | Your Anthropic API key (BYOK model) |

**Request**
```json
{
  "pages": [
    { "id": "page-uuid", "data": "<base64 .rm data>" }
  ]
}
```

**Response**
```json
{
  "pages": [
    {
      "id": "page-uuid",
      "markdown": "# Meeting Notes\n\nDiscussed the Q1 roadmap...",
      "confidence": 0.92
    }
  ]
}
```

**Errors**
| Code | Description |
|------|-------------|
| `401` | Invalid or missing `x-api-key` |
| `MISSING_ANTHROPIC_KEY` | Handwriting detected but no `x-anthropic-key` provided |

## Development

```bash
pip install -r src/requirements.txt   # Install deps
pytest                                 # Run tests
pytest tests/test_handler.py -v       # Single file
API_KEY=test-key ./scripts/test-local.sh path/to/page.rm
```

## Deployment

```bash
# Infrastructure
cd terraform && terraform init && terraform apply

# Lambda code
./scripts/deploy.sh
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_KEY_SECRET_ARN` | Secrets Manager ARN for Lambda auth key |
| `API_KEY` | Local override for testing |

## Security

**Bring Your Own Key (BYOK)** — Users provide their Anthropic API key per-request via `x-anthropic-key`. Keys pass through to Anthropic but are never stored or logged. Typed-text-only pages skip Claude Vision entirely.

## Dependencies

| Package | Purpose |
|---------|---------|
| [rmscene](https://github.com/ricklupton/rmscene) | Parse .rm v6 files |
| Pillow | Render strokes to PNG |
| anthropic | Claude Vision API |
| boto3 | AWS Secrets Manager |

## Related

- [Prose](https://github.com/solo-ist/prose) — Writing app that consumes this API
