# secrets.tf - Secrets Manager for API key authentication

# API key for authenticating requests to our Lambda
resource "aws_secretsmanager_secret" "api_key" {
  name        = "${var.project_name}/api-key"
  description = "API key for authenticating Lambda Function URL requests"
}

# Generate a random API key
resource "random_password" "api_key" {
  length  = 32
  special = false
}

# Store the generated API key
resource "aws_secretsmanager_secret_version" "api_key" {
  secret_id     = aws_secretsmanager_secret.api_key.id
  secret_string = random_password.api_key.result
}

# Anthropic API key for Claude Vision OCR
resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name        = "${var.project_name}/anthropic-api-key"
  description = "Anthropic API key for Claude Vision OCR"
}

resource "aws_secretsmanager_secret_version" "anthropic_api_key" {
  secret_id     = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = var.anthropic_api_key
}

variable "anthropic_api_key" {
  description = "Anthropic API key for Claude Vision OCR"
  type        = string
  sensitive   = true
}
