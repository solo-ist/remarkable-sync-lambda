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
# Note: The rotation script (scripts/rotate-key.sh) transitions this to a
# JSON array format ["new-key", "old-key"] for dual-key grace periods.
# The Lambda handles both plain string and JSON array formats.
resource "aws_secretsmanager_secret_version" "api_key" {
  secret_id     = aws_secretsmanager_secret.api_key.id
  secret_string = random_password.api_key.result
}
