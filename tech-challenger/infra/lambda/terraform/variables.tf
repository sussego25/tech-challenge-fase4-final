variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "tech-challenger"
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}

variable "lambda_role_arn" {
  description = "ARN da IAM role que a Lambda assumira"
  type        = string
}

variable "s3_bucket_name" {
  description = "Nome do bucket S3 de diagramas (variavel de ambiente da Lambda)"
  type        = string
}

variable "sqs_queue_url" {
  description = "URL da fila SQS de analise de arquitetura (variavel de ambiente da Lambda)"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Nome da tabela DynamoDB de diagramas (variavel de ambiente da Lambda)"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN do bucket S3 de diagramas (para permissao de invocacao pelo S3)"
  type        = string
}


