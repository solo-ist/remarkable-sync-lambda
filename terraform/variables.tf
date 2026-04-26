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
  description = "Lambda memory in MB (more memory = more CPU). 2048 MB roughly doubles vCPU vs 1024 MB, which speeds up Pillow stroke rendering. The pipeline is mostly I/O-bound waiting on Claude, so the win is modest but cheap."
  type        = number
  default     = 2048
}
