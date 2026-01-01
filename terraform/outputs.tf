# outputs.tf - Values to display after deployment

output "function_url" {
  description = "HTTPS endpoint for the Lambda"
  value       = aws_lambda_function_url.remarkable_sync.function_url
}

output "lambda_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.remarkable_sync.arn
}

output "api_key_secret_arn" {
  description = "ARN of the API key secret (retrieve value with: aws secretsmanager get-secret-value)"
  value       = aws_secretsmanager_secret.api_key.arn
}

output "rmapi_config_secret_arn" {
  description = "ARN of the rmapi config secret (you need to populate this)"
  value       = aws_secretsmanager_secret.rmapi_config.arn
}
