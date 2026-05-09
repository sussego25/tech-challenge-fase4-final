output "sagemaker_execution_role_arn" {
  description = "ARN da role de execucao do SageMaker"
  value       = aws_iam_role.sagemaker_execution_role.arn
}

output "endpoint_name" {
  description = "Nome do endpoint SageMaker LLM"
  value       = aws_sagemaker_endpoint.llm.name
}

output "endpoint_arn" {
  description = "ARN do endpoint SageMaker LLM"
  value       = aws_sagemaker_endpoint.llm.arn
}
