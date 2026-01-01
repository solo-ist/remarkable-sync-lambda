# main.tf - Provider configuration and shared resources

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure the AWS provider
# Uses credentials from ~/.aws/credentials by default
provider "aws" {
  region = var.aws_region
}

# Data source to get current AWS account info
# Useful for constructing ARNs dynamically
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
