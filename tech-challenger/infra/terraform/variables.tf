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
  default = {
    Terraform = "true"
    Project   = "tech-challenger"
  }
}

variable "enable_worker_iam" {
  description = "Habilita criacao da role IRSA do worker no EKS"
  type        = bool
  default     = false
}

variable "eks_oidc_provider_arn" {
  description = "ARN do provider OIDC do EKS (obrigatorio quando enable_worker_iam=true)"
  type        = string
  default     = ""
}

variable "eks_oidc_provider_url" {
  description = "URL do provider OIDC do EKS (obrigatorio quando enable_worker_iam=true)"
  type        = string
  default     = ""
}

variable "k8s_namespace" {
  description = "Namespace Kubernetes do worker"
  type        = string
  default     = "default"
}

variable "k8s_service_account_name" {
  description = "ServiceAccount Kubernetes usada pelo worker"
  type        = string
  default     = "worker-service"
}

variable "s3_lifecycle_expiration_days" {
  description = "Dias para expirar objetos no bucket S3 de diagramas"
  type        = number
  default     = 90
}



# ─────────────────────────────────────────────
# Networking (VPC)
# ─────────────────────────────────────────────
variable "enable_networking" {
  description = "Habilita criacao da VPC e subnets pelo modulo networking"
  type        = bool
  default     = false
}

variable "vpc_cidr" {
  description = "CIDR block da VPC (usado quando enable_networking=true)"
  type        = string
  default     = "10.0.0.0/16"
}

variable "enable_ha_nat" {
  description = "Habilita HA NAT Gateway (um por AZ). Recomendado para producao."
  type        = bool
  default     = false
}

# ─────────────────────────────────────────────
# EKS Cluster
# ─────────────────────────────────────────────
variable "enable_eks" {
  description = "Habilita criacao do cluster EKS"
  type        = bool
  default     = false
}

variable "eks_cluster_version" {
  description = "Versao do Kubernetes para o cluster EKS"
  type        = string
  default     = "1.30"
}

variable "eks_vpc_id" {
  description = "ID da VPC para o cluster EKS (obrigatorio quando enable_eks=true)"
  type        = string
  default     = ""
}

variable "eks_subnet_ids" {
  description = "IDs das subnets para o cluster EKS (minimo 2 AZs)"
  type        = list(string)
  default     = []
}

variable "eks_node_instance_type" {
  description = "Tipo de instancia EC2 para os nodes do EKS (t3.small para dev)"
  type        = string
  default     = "t3.small"
}

variable "eks_node_desired_size" {
  description = "Numero desejado de nodes"
  type        = number
  default     = 1
}

variable "eks_node_min_size" {
  description = "Numero minimo de nodes"
  type        = number
  default     = 1
}

variable "eks_node_max_size" {
  description = "Numero maximo de nodes"
  type        = number
  default     = 2
}

# ─────────────────────────────────────────────
# SageMaker
# ─────────────────────────────────────────────
variable "enable_sagemaker" {
  description = "Habilita criacao do endpoint SageMaker LLM"
  type        = bool
  default     = false
}

variable "sagemaker_model_container_image" {
  description = "URI da imagem de container do modelo LLM no ECR"
  type        = string
  default     = ""
}

variable "sagemaker_model_data_url" {
  description = "URI do artefato do modelo em S3 (model.tar.gz) para SageMaker custom model"
  type        = string
  default     = ""
}

variable "sagemaker_hf_model_id" {
  description = "HuggingFace model ID para o endpoint SageMaker"
  type        = string
  default     = "mistralai/Mistral-7B-Instruct-v0.2"
}

variable "sagemaker_instance_type" {
  description = "Tipo de instancia SageMaker (ml.m5.large para dev, GPU para prod)"
  type        = string
  default     = "ml.m5.large"
}

variable "sagemaker_instance_count" {
  description = "Numero de instancias no endpoint SageMaker"
  type        = number
  default     = 1
}

variable "enable_yolo_sagemaker" {
  description = "Habilita criacao do endpoint SageMaker YOLO"
  type        = bool
  default     = false
}

variable "yolo_sagemaker_model_container_image" {
  description = "URI da imagem de inferencia PyTorch/SageMaker usada pelo modelo YOLO"
  type        = string
  default     = ""
}

variable "yolo_sagemaker_model_data_url" {
  description = "URI S3 do artefato YOLO model.tar.gz"
  type        = string
  default     = ""
}

variable "yolo_sagemaker_instance_type" {
  description = "Tipo de instancia SageMaker para o endpoint YOLO"
  type        = string
  default     = "ml.m5.large"
}

variable "yolo_sagemaker_instance_count" {
  description = "Numero de instancias no endpoint YOLO"
  type        = number
  default     = 1
}

# ─────────────────────────────────────────────
# ECR
# ─────────────────────────────────────────────
variable "ecr_repository_names" {
  description = "Lista de nomes de repositorios ECR a criar"
  type        = list(string)
  default     = ["worker-service", "yolo-inference"]
}

variable "ecr_image_retention_count" {
  description = "Numero maximo de imagens a manter por repositorio ECR"
  type        = number
  default     = 10
}
