#!/bin/bash
set -e

# Deploy Lambda function
# Usage: ./scripts/deploy.sh

cd "$(dirname "$0")/.."

echo "📦 Building TypeScript..."
cd src
npm run build

echo "📦 Creating deployment package..."
cd dist
cp ../package.json .
cp -r ../node_modules .
zip -rq ../../lambda.zip . -x "*.map" -x "*.d.ts"
rm -rf node_modules package.json
cd ../..

echo "🚀 Deploying to Lambda..."
aws lambda update-function-code \
  --function-name remarkable-sync \
  --zip-file fileb://lambda.zip \
  --output text

rm lambda.zip

echo "✅ Deployment complete!"
