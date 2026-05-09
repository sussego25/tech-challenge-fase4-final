variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "tech-challenger"
}

variable "sqs_queue_arn" {
  description = "ARN da fila SQS principal de analise de arquitetura"
  type        = string
}

variable "dynamodb_diagrams_table_arn" {
  description = "ARN da tabela DynamoDB de diagramas"
  type        = string
}

variable "s3_diagrams_bucket_arn" {
  description = "ARN do bucket S3 de diagramas"
  type        = string
}

variable "common_tags" {
  description = "Common tags"
  type        = map(string)
  default = {
    Terraform = "true"
    Project   = "tech-challenger"
  }
}
