# Project Inception: reMarkable Sync Lambda

## Problem Statement

reMarkable tablets are excellent for handwritten notes, but the content is locked in a proprietary format. Users want to:
1. Access their handwritten notes as searchable text
2. Integrate notes into their writing workflow (Prose app)
3. Keep a local backup of their notebooks as markdown files

## Solution

A serverless AWS Lambda function that:
- Authenticates with reMarkable Cloud
- Downloads notebook files
- Performs OCR using AWS Textract
- Returns structured markdown content

The Prose desktop app polls this Lambda to sync notebooks to a local directory.

## Scope

### In Scope (MVP)

1. **Authentication**
   - Store rmapi credentials in AWS Secrets Manager
   - One-time manual setup of rmapi auth tokens

2. **Sync Endpoint**
   - Single POST endpoint that returns all notebooks
   - Full sync on each request (no delta/incremental)

3. **OCR Processing**
   - Convert .rm files to images
   - Use AWS Textract for handwriting recognition
   - Basic markdown formatting (headings, paragraphs)

4. **Infrastructure**
   - Lambda Function URL (no API Gateway needed)
   - Simple API key authentication via `x-api-key` header
   - Terraform for IaC

### Out of Scope (Future)

- Delta sync (only changed notebooks)
- Two-way sync (push edits back to reMarkable)
- Real-time streaming of OCR results
- Multiple user support
- PDF export
- Template detection (lined paper, etc.)

## Technical Decisions

### Why Lambda + Function URL?

- **Cost**: Pay only when syncing (likely 1-2x per day)
- **Simplicity**: No API Gateway complexity
- **Cold starts acceptable**: Sync is not latency-sensitive

### Why rmapi?

- Mature, well-maintained Go library
- Can be compiled as a static binary for Lambda
- Handles reMarkable Cloud authentication

### Why Textract over other OCR?

- Native AWS integration (IAM, no extra credentials)
- Good handwriting recognition
- Pay-per-use pricing

### Authentication Flow

1. User runs `rmapi` locally once to authenticate
2. User copies `~/.rmapi` config file contents
3. User stores config in AWS Secrets Manager
4. Lambda reads config on each invocation

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Account                          │
│                                                             │
│  ┌─────────────────┐      ┌─────────────────────────────┐  │
│  │ Secrets Manager │      │         Lambda              │  │
│  │                 │◄─────│                             │  │
│  │ rmapi config    │      │  1. Read rmapi config       │  │
│  └─────────────────┘      │  2. Download notebooks      │  │
│                           │  3. Convert to images       │  │
│                           │  4. Call Textract           │  │
│                           │  5. Format as markdown      │  │
│                           │  6. Return JSON response    │  │
│                           │                             │  │
│                           └──────────────┬──────────────┘  │
│                                          │                  │
│                                          │ Function URL     │
│                                          │ + API Key        │
└──────────────────────────────────────────┼──────────────────┘
                                           │
                                           ▼
                                    ┌─────────────┐
                                    │  Prose App  │
                                    │             │
                                    │ Polls every │
                                    │ 30 minutes  │
                                    └─────────────┘
```

## File Structure

```
remarkable-sync-lambda/
├── README.md
├── docs/
│   └── INCEPTION.md
├── src/
│   ├── handler.py          # Lambda entry point
│   ├── rmapi_client.py     # rmapi wrapper
│   ├── textract_client.py  # Textract wrapper
│   └── markdown_formatter.py
├── bin/
│   └── rmapi               # Compiled rmapi binary (Linux AMD64)
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── lambda.tf
├── tests/
│   └── ...
├── requirements.txt
└── template.yaml           # SAM template (optional)
```

## Success Criteria

1. **Functional**: Prose app can sync notebooks via the Lambda
2. **Reliable**: Handles network errors, rate limits gracefully
3. **Secure**: No credentials exposed, API key required
4. **Cost-effective**: < $5/month for typical usage

## Milestones

1. **M1: Infrastructure** - Terraform, Lambda shell, Function URL
2. **M2: rmapi Integration** - Download notebooks from reMarkable Cloud
3. **M3: OCR Pipeline** - Textract integration, markdown output
4. **M4: Production Ready** - Error handling, logging, monitoring

## Open Questions

1. How to handle large notebooks (many pages)?
   - *Tentative*: Process pages in parallel, set reasonable timeout

2. How to handle rmapi token refresh?
   - *Tentative*: Tokens are long-lived; manual refresh if needed

3. Rate limits on reMarkable Cloud API?
   - *Tentative*: Unknown; add exponential backoff

## References

- [rmapi GitHub](https://github.com/juruen/rmapi)
- [reMarkable .rm file format](https://remarkablewiki.com/tech/filesystem)
- [AWS Textract pricing](https://aws.amazon.com/textract/pricing/)
- [Lambda Function URLs](https://docs.aws.amazon.com/lambda/latest/dg/urls-configuration.html)
