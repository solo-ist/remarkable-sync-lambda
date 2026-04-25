"""End-to-end accuracy smoke test for the OCR pipeline.

This is the safety net for stroke-width / coordinate / scale changes in
rm_renderer.py and prompt-shape changes in claude_client.py. It runs the
full pipeline against a real .rm file and asserts that key tokens from a
known transcription appear in the output.

To enable, drop two files into `tests/fixtures/`:

  sample.rm      — a real .rm v6 file from a reMarkable tablet (handwriting
                   recommended; pure-typed pages skip the OCR path entirely)
  sample.txt     — expected tokens, one per line. Lines starting with `#`
                   are comments. Tokens are matched case-insensitively as
                   substrings; no need to capture full sentences.

Then set ANTHROPIC_API_KEY and run:

  ANTHROPIC_API_KEY=sk-... python3.11 -m pytest tests/test_ocr_accuracy.py -v -s

Without all three (sample.rm, sample.txt, ANTHROPIC_API_KEY), the tests
SKIP cleanly so CI stays green and contributors without a tablet aren't
blocked.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "src")

FIXTURE_DIR = Path(__file__).parent / "fixtures"
SAMPLE_RM = FIXTURE_DIR / "sample.rm"
SAMPLE_EXPECTED = FIXTURE_DIR / "sample.txt"

# Fraction of expected tokens that must appear in OCR output for the test
# to pass. 0.7 is a deliberate floor — Claude Vision is not perfect on
# cursive, and we'd rather catch *catastrophic* regressions (PNG resize
# breaks coordinates, prompt change collapses output) than false-positive on
# normal OCR variance.
ACCURACY_THRESHOLD = 0.7


@pytest.fixture
def rm_bytes():
    if not SAMPLE_RM.exists():
        pytest.skip(
            "No sample.rm fixture — drop a real .rm v6 file at "
            f"{SAMPLE_RM.relative_to(Path.cwd())} to enable accuracy tests"
        )
    return SAMPLE_RM.read_bytes()


@pytest.fixture
def expected_tokens():
    if not SAMPLE_EXPECTED.exists():
        pytest.skip(
            f"No expected-tokens manifest at {SAMPLE_EXPECTED.relative_to(Path.cwd())}"
        )
    lines = SAMPLE_EXPECTED.read_text().splitlines()
    tokens = [t.strip() for t in lines if t.strip() and not t.strip().startswith("#")]
    if not tokens:
        pytest.skip("sample.txt has no expected tokens")
    return tokens


@pytest.fixture
def anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set — skipping live OCR accuracy test")
    import anthropic
    return anthropic.Anthropic(api_key=api_key)


def _run_pipeline_and_count_matches(rm_bytes, anthropic_client, expected_tokens, scale):
    """Render → Claude → count token matches. Shared by the scale variants."""
    from rm_renderer import render_rm_to_png, has_strokes, extract_typed_text
    from claude_client import extract_text_from_image

    typed = extract_typed_text(rm_bytes) or ""
    png_bytes = render_rm_to_png(rm_bytes, scale=scale) if has_strokes(rm_bytes) else None

    handwriting_text = ""
    if png_bytes is not None:
        handwriting_text, _ = extract_text_from_image(png_bytes, anthropic_client)

    combined = (typed + "\n" + handwriting_text).lower()
    found = [t for t in expected_tokens if t.lower() in combined]
    return found, combined


def test_ocr_accuracy_at_default_scale(rm_bytes, expected_tokens, anthropic_client):
    """Default render scale (RENDER_SCALE) preserves OCR quality."""
    from rm_renderer import RENDER_SCALE

    found, combined = _run_pipeline_and_count_matches(
        rm_bytes, anthropic_client, expected_tokens, scale=RENDER_SCALE
    )
    threshold = max(1, int(len(expected_tokens) * ACCURACY_THRESHOLD))
    assert len(found) >= threshold, (
        f"OCR matched only {len(found)}/{len(expected_tokens)} tokens at "
        f"scale={RENDER_SCALE}.\n"
        f"Expected: {expected_tokens}\n"
        f"Found: {found}\n"
        f"Output: {combined!r}"
    )


def test_ocr_accuracy_at_full_scale(rm_bytes, expected_tokens, anthropic_client):
    """Full-resolution render is the ceiling we're benchmarking against."""
    found, combined = _run_pipeline_and_count_matches(
        rm_bytes, anthropic_client, expected_tokens, scale=1.0
    )
    threshold = max(1, int(len(expected_tokens) * ACCURACY_THRESHOLD))
    assert len(found) >= threshold, (
        f"OCR matched only {len(found)}/{len(expected_tokens)} tokens at "
        f"scale=1.0.\n"
        f"Expected: {expected_tokens}\n"
        f"Found: {found}\n"
        f"Output: {combined!r}"
    )
