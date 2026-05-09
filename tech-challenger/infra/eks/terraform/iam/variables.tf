variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "tech-challenger"
}

variable "eks_oidc_provider_arn" {
  description = "ARN do provider OIDC do EKS"
  type        = string
}

variable "eks_oidc_provider_url" {
  description = "URL do provider OIDC do EKS sem https://"
  type        = string
}

variable "k8s_namespace" {
  description = "Namespace Kubernetes do worker"
  type        = string
  default     = "default"
}

variable "k8s_service_account_name" {
  description = "ServiceAccount Kubernetes usada pelo worker"
  type        = string
}

variable "sqs_queue_arn" {
  description = "ARN da fila SQS principal"
  type        = string
}

variable "sqs_dlq_arn" {
  description = "ARN da DLQ"
  type        = string
}

variable "sns_topic_arn" {
  description = "ARN do topico SNS de resultados de analise"
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
