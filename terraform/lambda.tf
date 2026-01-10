# lambda.tf - Lambda function, IAM role, and Function URL

# IAM role that the Lambda assumes when running
# "AssumeRolePolicy" defines WHO can assume this role (the Lambda service)
resource "aws_iam_role" "remarkable_lambda" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# Policy defining WHAT the Lambda can do once it assumes the role
resource "aws_iam_role_policy" "remarkable_lambda" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.remarkable_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Write logs to CloudWatch
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        # Read API key from Secrets Manager
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.api_key.arn
        ]
      },
      {
        # OCR via AWS Textract
        Effect = "Allow"
        Action = [
          "textract:DetectDocumentText",
          "textract:AnalyzeDocument"
        ]
        Resource = "*"
      },
    ]
  })
}

# The Lambda function itself
# Note: We create a placeholder; actual code is deployed separately
resource "aws_lambda_function" "remarkable_sync" {
  function_name = var.project_name
  role          = aws_iam_role.remarkable_lambda.arn
  handler       = "handler.handler"
  runtime       = "python3.11"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory

  # Placeholder zip - will be replaced by actual deployment
  filename         = data.archive_file.lambda_placeholder.output_path
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256

  environment {
    variables = {
      API_KEY_SECRET_ARN = aws_secretsmanager_secret.api_key.arn
    }
  }
}

# Create a placeholder zip for initial deployment
data "archive_file" "lambda_placeholder" {
  type        = "zip"
  output_path = "${path.module}/placeholder.zip"

  source {
    content  = "def handler(event, context): return {'statusCode': 200, 'body': 'placeholder'}"
    filename = "handler.py"
  }
}

# Function URL - HTTPS endpoint without API Gateway
resource "aws_lambda_function_url" "remarkable_sync" {
  function_name      = aws_lambda_function.remarkable_sync.function_name
  authorization_type = "NONE" # We handle auth via x-api-key in code
}

# CloudWatch Log Group with retention
resource "aws_cloudwatch_log_group" "remarkable_lambda" {
  name              = "/aws/lambda/${var.project_name}"
  retention_in_days = 14
}
