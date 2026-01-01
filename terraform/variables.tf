# variables.tf - Input variables for the infrastructure

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "remarkable-sync"
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds (OCR can be slow)"
  type        = number
  default     = 300 # 5 minutes
}

variable "lambda_memory" {
  description = "Lambda memory in MB (more memory = more CPU)"
  type        = number
  default     = 1024
}
