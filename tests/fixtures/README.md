# OCR accuracy fixtures

`tests/test_ocr_accuracy.py` runs the full pipeline (render `.rm` → Claude
Vision → markdown) against a real tablet capture. It needs two files in
this directory:

- `sample.rm` — a real `.rm` v6 file (firmware 3.x) with handwriting.
  Pages with only typed text skip the OCR path and don't exercise the
  surface this test is protecting.
- `sample.txt` — expected tokens that should appear in the OCR output,
  one per line. Lines starting with `#` are comments. Matching is
  case-insensitive substring, so "lambda" will match "Lambda" or
  "AWS Lambda".

Run with:

```bash
ANTHROPIC_API_KEY=sk-... python3.11 -m pytest tests/test_ocr_accuracy.py -v -s
```

Without the fixtures or the env var, the test SKIPs cleanly.

## Capturing a sample from a tablet

Sync any handwritten notebook to your reMarkable Cloud account, then pull
one page's `.rm` file using `rmapi` (Go) or `rmapi-js` (Node) and copy it
here as `sample.rm`. Write down the tokens you actually wrote into
`sample.txt`.

This directory is checked into git so the smoke test runs the same
content for everyone — keep `sample.rm` small (one page) and the
content non-sensitive.
