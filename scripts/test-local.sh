#!/bin/bash
set -e

# Test Lambda handler locally
# Usage: ./scripts/test-local.sh [test.rm]

cd "$(dirname "$0")/.."

# Check if a .rm file was provided
RM_FILE="${1:-tests/fixtures/sample.rm}"

if [ ! -f "$RM_FILE" ]; then
  echo "Error: File not found: $RM_FILE"
  echo "Usage: ./scripts/test-local.sh [path/to/file.rm]"
  exit 1
fi

echo "Testing with: $RM_FILE"
echo "File size: $(wc -c < "$RM_FILE" | tr -d ' ') bytes"
echo ""

# Run the handler with the file path - let Python handle base64 encoding
cd src
python3 -c "
import json
import sys
import base64
sys.path.insert(0, '.')
from handler import handler

# Read and encode the .rm file
with open('$RM_FILE', 'rb') as f:
    rm_bytes = f.read()
base64_data = base64.b64encode(rm_bytes).decode('utf-8')

# Create test event
event = {
    'headers': {
        'x-api-key': '${API_KEY:-test-key}'
    },
    'requestContext': {
        'http': {
            'method': 'POST'
        }
    },
    'body': json.dumps({'pages': [{'id': 'test-page', 'data': base64_data}]})
}

result = handler(event, None)
print(json.dumps(json.loads(result.get('body', '{}')), indent=2))
"
