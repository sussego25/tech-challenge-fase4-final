output "endpoint_name" {
  description = "Nome do endpoint SageMaker YOLO"
  value       = aws_sagemaker_endpoint.yolo.name
}

output "endpoint_arn" {
  description = "ARN do endpoint SageMaker YOLO"
  value       = aws_sagemaker_endpoint.yolo.arn
}

output "sagemaker_execution_role_arn" {
  description = "ARN da role de execucao do SageMaker YOLO"
  value       = aws_iam_role.yolo_execution_role.arn
}



