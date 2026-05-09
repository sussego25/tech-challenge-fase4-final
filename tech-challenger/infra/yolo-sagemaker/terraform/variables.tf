variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}

variable "s3_diagrams_bucket_arn" {
  description = "ARN do bucket S3 de diagramas"
  type        = string
}

variable "model_container_image" {
  description = "URI da imagem de inferencia PyTorch/SageMaker usada pelo modelo YOLO"
  type        = string
}

variable "model_data_url" {
  description = "URI S3 do artefato YOLO model.tar.gz"
  type        = string
}

variable "instance_type" {
  description = "Tipo de instancia SageMaker para o endpoint YOLO"
  type        = string
  default     = "ml.m5.large"
}

variable "instance_count" {
  description = "Numero de instancias no endpoint YOLO"
  type        = number
  default     = 1
}
