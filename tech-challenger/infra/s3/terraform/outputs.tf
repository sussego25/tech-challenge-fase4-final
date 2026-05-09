output "diagrams_bucket_name" {
  description = "Nome do bucket S3 de diagramas"
  value       = aws_s3_bucket.diagrams.bucket
}

output "diagrams_bucket_arn" {
  description = "ARN do bucket S3 de diagramas"
  value       = aws_s3_bucket.diagrams.arn
}
