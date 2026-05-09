variable "aws_region" {
  description = "AWS Region"
  type        = string
}

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

variable "cluster_version" {
  description = "Versao do Kubernetes para o cluster EKS"
  type        = string
  default     = "1.30"
}

variable "vpc_id" {
  description = "ID da VPC onde o cluster EKS sera criado"
  type        = string
}

variable "subnet_ids" {
  description = "Lista de IDs de subnets (minimo 2 AZs) para o cluster e node groups"
  type        = list(string)
}

variable "node_instance_type" {
  description = "Tipo de instancia EC2 para os nodes"
  type        = string
  default     = "t3.medium"
}

variable "node_desired_size" {
  description = "Numero desejado de nodes no node group"
  type        = number
  default     = 2
}

variable "node_min_size" {
  description = "Numero minimo de nodes no node group"
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Numero maximo de nodes no node group"
  type        = number
  default     = 4
}

variable "node_disk_size" {
  description = "Tamanho do disco dos nodes em GB"
  type        = number
  default     = 20
}
