"""Tests for secrets module — JSON parsing, TTL caching, and env var fallback."""

import json
import sys
import time
from unittest.mock import patch, MagicMock

sys.path.insert(0, "src")

import secrets as secrets_module
from secrets import get_api_keys, CACHE_TTL_SECONDS


def _reset_cache():
    """Reset module-level cache state between tests."""
    secrets_module._cached_keys = None
    secrets_module._cache_time = 0


# --- Environment variable fallback ---


def test_env_var_override():
    """API_KEY env var returns single-element list."""
    _reset_cache()
    with patch.dict("os.environ", {"API_KEY": "env-test-key"}):
        result = get_api_keys()
        assert result == ["env-test-key"]


def test_env_var_skips_secrets_manager():
    """API_KEY env var bypasses Secrets Manager entirely."""
    _reset_cache()
    with patch.dict("os.environ", {"API_KEY": "local-key"}), \
         patch.object(secrets_module, "get_secrets_client") as mock_client:
        get_api_keys()
        mock_client.assert_not_called()


# --- JSON array parsing ---


def test_json_array_secret():
    """JSON array secret returns list of keys in order."""
    _reset_cache()
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps(["new-key", "old-key"])
    }
    with patch.dict("os.environ", {"API_KEY_SECRET_ARN": "arn:test"}, clear=False), \
         patch.object(secrets_module, "get_secrets_client", return_value=mock_client), \
         patch.dict("os.environ", {}, clear=False):
        # Remove API_KEY if set
        with patch.dict("os.environ", {"API_KEY_SECRET_ARN": "arn:test"}):
            import os
            os.environ.pop("API_KEY", None)
            result = get_api_keys()
            assert result == ["new-key", "old-key"]


def test_plain_string_secret():
    """Plain string secret returns single-element list."""
    _reset_cache()
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": "plain-api-key-no-json"
    }
    import os
    os.environ.pop("API_KEY", None)
    with patch.dict("os.environ", {"API_KEY_SECRET_ARN": "arn:test"}), \
         patch.object(secrets_module, "get_secrets_client", return_value=mock_client):
        result = get_api_keys()
        assert result == ["plain-api-key-no-json"]


def test_json_encoded_string_secret():
    """JSON-encoded string (not array) uses parsed value, not raw JSON."""
    _reset_cache()
    mock_client = MagicMock()
    # A JSON string like '"my-key"' — json.loads returns 'my-key' (without quotes)
    mock_client.get_secret_value.return_value = {
        "SecretString": '"my-key"'
    }
    import os
    os.environ.pop("API_KEY", None)
    with patch.dict("os.environ", {"API_KEY_SECRET_ARN": "arn:test"}), \
         patch.object(secrets_module, "get_secrets_client", return_value=mock_client):
        result = get_api_keys()
        assert result == ["my-key"]  # parsed, not ['"my-key"']


# --- TTL caching ---


def test_cache_returns_without_fetch():
    """Cached keys are returned without calling Secrets Manager."""
    _reset_cache()
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps(["cached-key"])
    }
    import os
    os.environ.pop("API_KEY", None)
    with patch.dict("os.environ", {"API_KEY_SECRET_ARN": "arn:test"}), \
         patch.object(secrets_module, "get_secrets_client", return_value=mock_client):
        # First call fetches
        get_api_keys()
        # Second call should use cache
        get_api_keys()
        assert mock_client.get_secret_value.call_count == 1


def test_cache_expires_after_ttl():
    """Cache expires after TTL and re-fetches from Secrets Manager."""
    _reset_cache()
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps(["key-v1"])
    }
    import os
    os.environ.pop("API_KEY", None)
    with patch.dict("os.environ", {"API_KEY_SECRET_ARN": "arn:test"}), \
         patch.object(secrets_module, "get_secrets_client", return_value=mock_client):
        get_api_keys()

        # Simulate TTL expiry
        secrets_module._cache_time = time.monotonic() - CACHE_TTL_SECONDS - 1

        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps(["key-v2"])
        }
        result = get_api_keys()
        assert result == ["key-v2"]
        assert mock_client.get_secret_value.call_count == 2


def test_empty_list_is_cached():
    """Empty list from Secrets Manager is still cached (no repeated fetches)."""
    _reset_cache()
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps([])
    }
    import os
    os.environ.pop("API_KEY", None)
    with patch.dict("os.environ", {"API_KEY_SECRET_ARN": "arn:test"}), \
         patch.object(secrets_module, "get_secrets_client", return_value=mock_client):
        get_api_keys()
        get_api_keys()
        assert mock_client.get_secret_value.call_count == 1


# --- Error cases ---


def test_missing_secret_arn_raises():
    """Missing API_KEY_SECRET_ARN raises ValueError."""
    _reset_cache()
    import os
    os.environ.pop("API_KEY", None)
    os.environ.pop("API_KEY_SECRET_ARN", None)
    with patch.dict("os.environ", {}, clear=False):
        try:
            get_api_keys()
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "API_KEY_SECRET_ARN" in str(e)
