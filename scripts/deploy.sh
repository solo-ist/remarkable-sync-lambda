#!/bin/bash
set -e

# Deploy Lambda function
# Usage: ./scripts/deploy.sh

cd "$(dirname "$0")/.."

PACKAGE_DIR="build/package"
LAMBDA_ZIP="lambda.zip"
FUNCTION_NAME="remarkable-sync"

echo "🧹 Cleaning previous build..."
rm -rf build "$LAMBDA_ZIP"
mkdir -p "$PACKAGE_DIR"

echo "📦 Installing Python dependencies for Lambda (linux x86_64)..."
pip3 install -r src/requirements.txt -t "$PACKAGE_DIR" \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.11 \
  --only-binary=:all: \
  --quiet

echo "📦 Copying source files..."
cp src/*.py "$PACKAGE_DIR/"

echo "📦 Creating deployment package..."
cd "$PACKAGE_DIR"
zip -rq "../../$LAMBDA_ZIP" . -x "*.pyc" -x "__pycache__/*" -x "*.dist-info/*"
cd ../..

echo "🚀 Deploying to Lambda..."
aws lambda update-function-code \
  --function-name "$FUNCTION_NAME" \
  --zip-file "fileb://$LAMBDA_ZIP" \
  --output text

echo "🧹 Cleaning up..."
rm -rf build "$LAMBDA_ZIP"

echo "✅ Deployment complete!"
