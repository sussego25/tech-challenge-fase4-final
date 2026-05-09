resource "aws_iam_role" "worker_service_role" {
  name = "${var.project_name}-worker-service-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowIRSAAssumeRole"
      Action = "sts:AssumeRoleWithWebIdentity"
      Effect = "Allow"
      Principal = {
        Federated = var.eks_oidc_provider_arn
      }
      Condition = {
        StringEquals = {
          "${var.eks_oidc_provider_url}:sub" = "system:serviceaccount:${var.k8s_namespace}:${var.k8s_service_account_name}"
          "${var.eks_oidc_provider_url}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy" "worker_sqs_policy" {
  name = "${var.project_name}-worker-sqs-policy-${var.environment}"
  role = aws_iam_role.worker_service_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowReceiveAndDeleteMessagesFromSQS"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = var.sqs_queue_arn
      },
      {
        Sid    = "AllowReceiveMessagesFromDLQ"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = var.sqs_dlq_arn
      }
    ]
  })
}

output "worker_service_role_arn" {
  description = "ARN da role do worker service para IRSA"
  value       = aws_iam_role.worker_service_role.arn
}

resource "aws_iam_role_policy" "worker_dynamodb_policy" {
  name = "${var.project_name}-worker-dynamodb-policy-${var.environment}"
  role = aws_iam_role.worker_service_role.id

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

resource "aws_iam_role_policy" "worker_sns_policy" {
  name = "${var.project_name}-worker-sns-policy-${var.environment}"
  role = aws_iam_role.worker_service_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "AllowPublishAnalysisResultsToSNS"
      Effect   = "Allow"
      Action   = ["sns:Publish"]
      Resource = var.sns_topic_arn
    }]
  })
}

resource "aws_iam_role_policy" "worker_s3_policy" {
  name = "${var.project_name}-worker-s3-policy-${var.environment}"
  role = aws_iam_role.worker_service_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowDiagramsBucketReadAccess"
      Effect = "Allow"
      Action = [
        "s3:GetObject"
      ]
      Resource = "${var.s3_diagrams_bucket_arn}/*"
    }]
  })
}

resource "aws_iam_role_policy" "worker_ai_invoke_policy" {
  name = "${var.project_name}-worker-ai-invoke-policy-${var.environment}"
  role = aws_iam_role.worker_service_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowInvokeYoloSageMakerEndpoint"
        Effect = "Allow"
        Action = [
          "sagemaker:InvokeEndpoint"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowInvokeBedrockModel"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "*"
      }
    ]
  })
}
