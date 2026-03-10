#!/bin/bash
set -e

# Rotate Lambda API key with dual-key grace period.
#
# Rotation flow:
#   1. ./scripts/rotate-key.sh              — generate new key, keep old key valid
#   2. Update Prose config with new key      — verify it works
#   3. ./scripts/rotate-key.sh --finalize    — remove old key(s)

cd "$(dirname "$0")/.."

SECRET_ARN="${SECRET_ARN:-$(cd terraform && terraform output -raw api_key_secret_arn 2>/dev/null || true)}"

if [ -z "$SECRET_ARN" ]; then
  echo "Error: Could not determine secret ARN."
  echo "Set SECRET_ARN env var or run from project root with terraform outputs."
  exit 1
fi

rotate() {
  echo "Fetching current key(s)..."
  local current
  current=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_ARN" \
    --query SecretString --output text)

  # Generate new key
  local new_key
  new_key=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

  # Build dual-key array: [new, ...old]
  local dual_keys
  dual_keys=$(echo "$current" | NEW_KEY="$new_key" python3 -c "
import json, os, sys
current = sys.stdin.read().strip()
try:
    keys = json.loads(current)
    if not isinstance(keys, list):
        keys = [current]
except (json.JSONDecodeError, TypeError):
    keys = [current]
print(json.dumps([os.environ['NEW_KEY']] + keys))
")

  aws secretsmanager put-secret-value \
    --secret-id "$SECRET_ARN" \
    --secret-string "$dual_keys" \
    --output text > /dev/null

  echo ""
  echo "New key is active. Both old and new keys are now valid."
  echo ""
  echo "New API key (copy to Prose config):"
  echo "  $new_key"
  echo ""
  echo "Next steps:"
  echo "  1. Update Prose with the new key above"
  echo "  2. Verify Prose works"
  echo "  3. Run: ./scripts/rotate-key.sh --finalize"
}

finalize() {
  echo "Fetching current key(s)..."
  local current
  current=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_ARN" \
    --query SecretString --output text)

  local key_count
  key_count=$(echo "$current" | python3 -c "
import json, sys
current = sys.stdin.read().strip()
try:
    keys = json.loads(current)
    print(len(keys) if isinstance(keys, list) else 1)
except:
    print(1)
")

  if [ "$key_count" -le 1 ]; then
    echo "Only one key active — nothing to finalize."
    exit 0
  fi

  echo "Removing old key(s), keeping only the primary (newest) key..."
  read -r -p "Confirm? Prose must already be using the new key. [y/N] " confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi

  local primary_only
  primary_only=$(echo "$current" | python3 -c "
import json, sys
current = sys.stdin.read().strip()
keys = json.loads(current)
print(json.dumps([keys[0]] if isinstance(keys, list) else [keys]))
")

  aws secretsmanager put-secret-value \
    --secret-id "$SECRET_ARN" \
    --secret-string "$primary_only" \
    --output text > /dev/null

  echo "Old key(s) removed. Only the primary key is now valid."
}

case "${1:-}" in
  --finalize)
    finalize
    ;;
  --help|-h)
    echo "Usage: ./scripts/rotate-key.sh [--finalize]"
    echo ""
    echo "  (no args)     Generate new key, keep old key valid"
    echo "  --finalize    Remove old key(s) after verifying Prose works"
    echo ""
    echo "Set SECRET_ARN env var or run from project root with terraform outputs."
    ;;
  *)
    rotate
    ;;
esac
