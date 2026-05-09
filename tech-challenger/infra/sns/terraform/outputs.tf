output "analysis_results_topic_arn" {
  description = "ARN do topico SNS com o JSON de analise salvo no DynamoDB"
  value       = aws_sns_topic.analysis_results.arn
}

output "analysis_results_topic_name" {
  description = "Nome do topico SNS com o JSON de analise salvo no DynamoDB"
  value       = aws_sns_topic.analysis_results.name
}
