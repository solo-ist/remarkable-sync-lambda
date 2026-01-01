# secrets.tf - Secrets Manager for rmapi credentials

# Secret container (metadata)
resource "aws_secretsmanager_secret" "rmapi_config" {
  name        = "${var.project_name}/rmapi-config"
  description = "reMarkable Cloud API credentials from rmapi"
}

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

# Note: rmapi_config secret value is set manually after running rmapi locally
# to authenticate with reMarkable Cloud
