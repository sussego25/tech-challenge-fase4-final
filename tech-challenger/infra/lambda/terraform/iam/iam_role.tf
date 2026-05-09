resource "aws_iam_role" "lambda_documents_role" {
  name = "${var.project_name}-lambda-documents-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowLambdaServiceAssumeRole"
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy" "lambda_sqs_send_policy" {
  name = "${var.project_name}-lambda-sqs-send-policy-${var.environment}"
  role = aws_iam_role.lambda_documents_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowSendMessageToArchitectureQueue"
      Effect = "Allow"
      Action = [
        "sqs:SendMessage"
      ]
      Resource = var.sqs_queue_arn
    }]
  })
}

resource "aws_iam_role_policy" "lambda_dynamodb_policy" {
  name = "${var.project_name}-lambda-dynamodb-policy-${var.environment}"
  role = aws_iam_role.lambda_documents_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowDiagramsTableAccess"
      Effect = "Allow"
      Action = [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem"
      ]
      Resource = var.dynamodb_diagrams_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "lambda_s3_policy" {
  name = "${var.project_name}-lambda-s3-policy-${var.environment}"
  role = aws_iam_role.lambda_documents_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowDiagramsBucketAccess"
      Effect = "Allow"
      Action = [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ]
      Resource = "${var.s3_diagrams_bucket_arn}/*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_documents_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

output "lambda_documents_role_arn" {
  description = "ARN da role da Lambda de documentos"
  value       = aws_iam_role.lambda_documents_role.arn
}
