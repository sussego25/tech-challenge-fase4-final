output "architecture_analysis_queue_url" {
  description = "URL of the architecture analysis SQS queue"
  value       = module.sqs.architecture_analysis_queue_url
}

output "architecture_analysis_queue_arn" {
  description = "ARN of the architecture analysis SQS queue"
  value       = module.sqs.architecture_analysis_queue_arn
}

output "architecture_analysis_dlq_url" {
  description = "URL of the architecture analysis DLQ"
  value       = module.sqs.architecture_analysis_dlq_url
}

output "architecture_analysis_dlq_arn" {
  description = "ARN of the architecture analysis DLQ"
  value       = module.sqs.architecture_analysis_dlq_arn
}

output "analysis_results_topic_arn" {
  description = "ARN do topico SNS que recebe o JSON de analise salvo no DynamoDB"
  value       = module.sns.analysis_results_topic_arn
}

output "analysis_results_topic_name" {
  description = "Nome do topico SNS que recebe o JSON de analise salvo no DynamoDB"
  value       = module.sns.analysis_results_topic_name
}

output "lambda_documents_role_arn" {
  description = "ARN da role da Lambda de documentos"
  value       = module.lambda_iam.lambda_documents_role_arn
}

output "worker_service_role_arn" {
  description = "ARN da role IRSA do worker no EKS (null quando enable_worker_iam=false)"
  value       = try(module.worker_iam[0].worker_service_role_arn, null)
}

output "diagrams_table_name" {
  description = "Nome da tabela DynamoDB de diagramas"
  value       = module.dynamodb.diagrams_table_name
}

output "diagrams_table_arn" {
  description = "ARN da tabela DynamoDB de diagramas"
  value       = module.dynamodb.diagrams_table_arn
}

output "diagrams_bucket_name" {
  description = "Nome do bucket S3 de diagramas"
  value       = module.s3.diagrams_bucket_name
}

output "diagrams_bucket_arn" {
  description = "ARN do bucket S3 de diagramas"
  value       = module.s3.diagrams_bucket_arn
}

output "lambda_function_name" {
  description = "Nome da funcao Lambda order-handler"
  value       = module.lambda.lambda_function_name
}

output "lambda_function_arn" {
  description = "ARN da funcao Lambda order-handler"
  value       = module.lambda.lambda_function_arn
}

# ─────────────────────────────────────────────
# Networking (VPC)
# ─────────────────────────────────────────────
output "vpc_id" {
  description = "ID da VPC (null quando enable_networking=false)"
  value       = try(module.networking[0].vpc_id, null)
}

output "public_subnet_ids" {
  description = "IDs das subnets publicas (null quando enable_networking=false)"
  value       = try(module.networking[0].public_subnet_ids, null)
}

output "private_subnet_ids" {
  description = "IDs das subnets privadas (null quando enable_networking=false)"
  value       = try(module.networking[0].private_subnet_ids, null)
}

output "eks_nodes_security_group_id" {
  description = "ID do security group para nodes EKS (null quando enable_networking=false)"
  value       = try(module.networking[0].eks_nodes_security_group_id, null)
}

# ─────────────────────────────────────────────
# EKS
# ─────────────────────────────────────────────
output "eks_cluster_name" {
  description = "Nome do cluster EKS (null quando enable_eks=false)"
  value       = try(module.eks[0].cluster_name, null)
}

output "eks_cluster_endpoint" {
  description = "Endpoint do cluster EKS (null quando enable_eks=false)"
  value       = try(module.eks[0].cluster_endpoint, null)
}

output "eks_oidc_provider_arn" {
  description = "ARN do OIDC provider do EKS para IRSA (null quando enable_eks=false)"
  value       = try(module.eks[0].oidc_provider_arn, null)
}

output "eks_oidc_provider_url" {
  description = "URL do OIDC provider do EKS para IRSA (null quando enable_eks=false)"
  value       = try(module.eks[0].oidc_provider_url, null)
}

# ─────────────────────────────────────────────
# SageMaker
# ─────────────────────────────────────────────
output "sagemaker_endpoint_name" {
  description = "Nome do endpoint SageMaker LLM (null quando enable_sagemaker=false)"
  value       = try(module.sagemaker[0].endpoint_name, null)
}

output "sagemaker_endpoint_arn" {
  description = "ARN do endpoint SageMaker LLM (null quando enable_sagemaker=false)"
  value       = try(module.sagemaker[0].endpoint_arn, null)
}

output "sagemaker_execution_role_arn" {
  description = "ARN da execution role do SageMaker (null quando enable_sagemaker=false)"
  value       = try(module.sagemaker[0].sagemaker_execution_role_arn, null)
}

output "yolo_sagemaker_endpoint_name" {
  description = "Nome do endpoint SageMaker YOLO (null quando enable_yolo_sagemaker=false)"
  value       = try(module.yolo_sagemaker[0].endpoint_name, null)
}

output "yolo_sagemaker_endpoint_arn" {
  description = "ARN do endpoint SageMaker YOLO (null quando enable_yolo_sagemaker=false)"
  value       = try(module.yolo_sagemaker[0].endpoint_arn, null)
}

output "yolo_sagemaker_execution_role_arn" {
  description = "ARN da execution role do SageMaker YOLO (null quando enable_yolo_sagemaker=false)"
  value       = try(module.yolo_sagemaker[0].sagemaker_execution_role_arn, null)
}

# ─────────────────────────────────────────────
# ECR
# ─────────────────────────────────────────────
output "ecr_repository_urls" {
  description = "Map de nome do repositorio para URL do ECR"
  value       = module.ecr.repository_urls
}

output "ecr_repository_arns" {
  description = "Map de nome do repositorio para ARN do ECR"
  value       = module.ecr.repository_arns
}
