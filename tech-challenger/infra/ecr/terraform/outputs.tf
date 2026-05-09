output "repository_urls" {
  description = "Map de nome do repositorio para URL do ECR"
  value       = { for k, v in aws_ecr_repository.services : k => v.repository_url }
}

output "repository_arns" {
  description = "Map de nome do repositorio para ARN do ECR"
  value       = { for k, v in aws_ecr_repository.services : k => v.arn }
}
