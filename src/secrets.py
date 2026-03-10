"""AWS Secrets Manager helper with TTL-based caching for Lambda container reuse."""

import json
import os
import time
import boto3

secrets_client = None

# TTL cache state
_cached_keys: list[str] | None = None
_cache_time: float = 0
CACHE_TTL_SECONDS = 300  # 5 minutes — short enough for rotation, low overhead for sporadic traffic


def get_secrets_client():
    """Lazy initialization of Secrets Manager client."""
    global secrets_client
    if secrets_client is None:
        secrets_client = boto3.client("secretsmanager")
    return secrets_client


def get_api_keys() -> list[str]:
    """Get valid API keys from Secrets Manager (cached with TTL).

    Returns a list of valid keys ordered by recency (primary first).
    During rotation, both old and new keys are valid.

    The secret value can be either:
    - A JSON array: ["newest-key", "old-key"]
    - A plain string: "single-key" (backward compatible)

    Falls back to API_KEY environment variable for local testing.
    """
    global _cached_keys, _cache_time

    # Check environment variable first (local testing)
    if api_key := os.environ.get("API_KEY"):
        return [api_key]

    # Return cached keys if still valid
    if _cached_keys and (time.monotonic() - _cache_time) < CACHE_TTL_SECONDS:
        return _cached_keys

    # Get from Secrets Manager
    secret_arn = os.environ.get("API_KEY_SECRET_ARN")
    if not secret_arn:
        raise ValueError("API_KEY_SECRET_ARN environment variable not set")

    client = get_secrets_client()
    response = client.get_secret_value(SecretId=secret_arn)
    secret_string = response["SecretString"]

    # Parse as JSON array, fall back to plain string for backward compat
    try:
        parsed = json.loads(secret_string)
        if isinstance(parsed, list):
            _cached_keys = parsed
        else:
            _cached_keys = [secret_string]
    except (json.JSONDecodeError, TypeError):
        _cached_keys = [secret_string]

    _cache_time = time.monotonic()
    return _cached_keys
