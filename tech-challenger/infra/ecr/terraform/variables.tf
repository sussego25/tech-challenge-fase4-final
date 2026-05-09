variable "environment" {
  description = "Ambiente (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Nome do projeto"
  type        = string
}

variable "repository_names" {
  description = "Lista de nomes de repositorios ECR"
  type        = list(string)
  default     = ["worker-service", "yolo-inference"]
}

variable "image_retention_count" {
  description = "Numero maximo de imagens a manter por repositorio"
  type        = number
  default     = 10
}

variable "common_tags" {
  description = "Tags comuns"
  type        = map(string)
  default     = {}
}
