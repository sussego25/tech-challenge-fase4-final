output "architecture_analysis_queue_url" {
  description = "URL of the architecture analysis SQS queue"
  value       = aws_sqs_queue.architecture_analysis_queue.url
}

output "architecture_analysis_queue_arn" {
  description = "ARN of the architecture analysis SQS queue"
  value       = aws_sqs_queue.architecture_analysis_queue.arn
}

output "architecture_analysis_dlq_url" {
  description = "URL of the architecture analysis DLQ"
  value       = aws_sqs_queue.architecture_analysis_dlq.url
}

output "architecture_analysis_dlq_arn" {
  description = "ARN of the architecture analysis DLQ"
  value       = aws_sqs_queue.architecture_analysis_dlq.arn
}
