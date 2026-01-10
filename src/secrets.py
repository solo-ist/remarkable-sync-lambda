"""AWS Secrets Manager helper with caching for Lambda container reuse."""

import os
import boto3
from functools import lru_cache

secrets_client = None


def get_secrets_client():
    """Lazy initialization of Secrets Manager client."""
    global secrets_client
    if secrets_client is None:
        secrets_client = boto3.client("secretsmanager")
    return secrets_client


@lru_cache(maxsize=1)
def get_api_key() -> str:
    """Get API key from Secrets Manager (cached for Lambda reuse).

    Falls back to API_KEY environment variable for local testing.
    """
    # Check environment variable first (local testing)
    if api_key := os.environ.get("API_KEY"):
        return api_key

    # Get from Secrets Manager
    secret_arn = os.environ.get("API_KEY_SECRET_ARN")
    if not secret_arn:
        raise ValueError("API_KEY_SECRET_ARN environment variable not set")

    client = get_secrets_client()
    response = client.get_secret_value(SecretId=secret_arn)
    return response["SecretString"]


@lru_cache(maxsize=1)
def get_anthropic_api_key() -> str:
    """Get Anthropic API key from Secrets Manager (cached for Lambda reuse).

    Falls back to ANTHROPIC_API_KEY environment variable for local testing.
    """
    # Check environment variable first (local testing)
    if api_key := os.environ.get("ANTHROPIC_API_KEY"):
        return api_key

    # Get from Secrets Manager
    secret_arn = os.environ.get("ANTHROPIC_API_KEY_SECRET_ARN")
    if not secret_arn:
        raise ValueError("ANTHROPIC_API_KEY_SECRET_ARN environment variable not set")

    client = get_secrets_client()
    response = client.get_secret_value(SecretId=secret_arn)
    return response["SecretString"]
