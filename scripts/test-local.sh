#!/bin/bash
set -e

# Test Lambda handler locally
# Usage: ./scripts/test-local.sh [test.rm]

cd "$(dirname "$0")/.."

# Check if a .rm file was provided
RM_FILE="${1:-tests/fixtures/sample.rm}"

if [ ! -f "$RM_FILE" ]; then
  echo "❌ File not found: $RM_FILE"
  echo "Usage: ./scripts/test-local.sh [path/to/file.rm]"
  exit 1
fi

# Base64 encode the .rm file
BASE64_DATA=$(base64 < "$RM_FILE")

# Create test event
EVENT=$(cat <<EOF
{
  "headers": {
    "x-api-key": "${API_KEY:-test-key}"
  },
  "requestContext": {
    "http": {
      "method": "POST"
    }
  },
  "body": "{\"pages\": [{\"id\": \"test-page\", \"data\": \"$BASE64_DATA\"}]}"
}
EOF
)

echo "🧪 Testing with: $RM_FILE"
echo "📦 File size: $(wc -c < "$RM_FILE" | tr -d ' ') bytes"
echo ""

# Run the handler
cd src
python3 -c "
import json
import sys
sys.path.insert(0, '.')
from handler import handler

event = json.loads('''$EVENT''')
result = handler(event, None)
print(json.dumps(json.loads(result.get('body', '{}')), indent=2))
"
