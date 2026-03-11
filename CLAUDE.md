# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AWS Lambda OCR service for reMarkable tablet notebooks. Receives .rm page files from the Prose desktop app, extracts text (typed or handwritten), and returns formatted markdown. The Prose app handles reMarkable Cloud auth and downloads via rmapi-js; this Lambda focuses solely on OCR.

## Commands

```bash
# Install dependencies (use venv)
source .venv/bin/activate
pip install -r src/requirements.txt

# Run all tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# Run single test file
pytest tests/test_handler.py -v

# Run single test
pytest tests/test_handler.py::test_valid_request_structure -v

# Deploy Lambda code only
./scripts/deploy.sh

# Deploy infrastructure changes
cd terraform && terraform apply

# Get deployed API key
terraform -chdir=terraform output -raw api_key
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

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/) format (see parent `~/Code/CLAUDE.md` for full guidelines):

```
<type>(<scope>): <subject>

<body>

Fixes #123
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Rules:**
- Subject: lowercase, no period, max 50 chars
- Body: explain *what* and *why*, wrap at 72 chars
- Footer: reference issues with `Fixes #N` or `Refs #N`

## GitHub Workflow

This project uses an issue-based development workflow:

### 1. Create Issue First
Before starting work, create or find a GitHub issue that describes the task:
- Bug fixes → describe the problem and reproduction steps
- Features → describe the desired behavior
- Chores → describe what needs to change and why

### 2. Work on Feature Branch
```bash
git checkout -b <type>/<short-description>
# Examples: fix/auth-header, feat/batch-processing, test/improve-coverage
```

### 3. Reference Issues in Commits
- Use `Refs #N` for related work
- Use `Fixes #N` (in final commit) to auto-close the issue when merged

### 4. Create PR Linking to Issue
```bash
gh pr create --title "<type>: <description>" --body "Closes #N"
```

### 5. Merge and Verify
- Squash merge to keep history clean
- Verify issue was auto-closed
- Delete the feature branch

### When to Create Issues
| Situation | Action |
|-----------|--------|
| Bug discovered during work | Create issue, continue or defer |
| Feature request from user | Create issue before starting |
| Refactor opportunity | Create issue, link to related work |
| Test coverage gaps | Create issue with specific targets |

## Troubleshooting

### Lambda Deployment

**"Module not found" errors after deploy:**
- Ensure `requirements.txt` is in `src/` directory
- Run `./scripts/deploy.sh` (not manual zip)

**API key validation failing:**
- Check `API_KEY_SECRET_ARN` is set in Lambda environment
- Verify secret exists: `aws secretsmanager get-secret-value --secret-id <arn>`

### Local Testing

**Tests can't import modules:**
```bash
source .venv/bin/activate  # Ensure venv is active
pip install -r src/requirements.txt
```

**rmscene parse errors:**
- Verify .rm file is v6 format (firmware 3.x)
- Check file isn't corrupted (try opening in reMarkable app)

### Claude Vision OCR

**Empty OCR results:**
- Check `_filter_non_text_response()` isn't catching valid text
- Verify PNG rendering produces visible strokes (save intermediate PNG)

**"Anthropic API key required" error:**
- Only thrown for pages with handwriting strokes
- Typed-only pages work without Anthropic key

## Development Notes

- Pure Python dependencies (rmscene, Pillow, anthropic) — no native libraries needed
- rmscene supports .rm v6 format (reMarkable firmware 3.x)
- Typed text extracted directly from .rm files (firmware v3.3+)
- reMarkable uses center-origin X coordinates; `rm_renderer.py` applies `X_OFFSET = 702` to convert
