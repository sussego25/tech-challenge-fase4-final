output "diagrams_table_name" {
  description = "Nome da tabela DynamoDB de diagramas"
  value       = aws_dynamodb_table.diagrams.name
}

output "diagrams_table_arn" {
  description = "ARN da tabela DynamoDB de diagramas"
  value       = aws_dynamodb_table.diagrams.arn
}

