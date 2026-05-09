# ─────────────────────────────────────────────
# IAM: execution role para o SageMaker
# ─────────────────────────────────────────────
resource "aws_iam_role" "sagemaker_execution_role" {
  name = "${var.project_name}-sagemaker-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "sagemaker.amazonaws.com" }
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "sagemaker_full_access" {
  role       = aws_iam_role.sagemaker_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

# Acesso de leitura ao bucket S3 de diagramas
resource "aws_iam_role_policy" "sagemaker_s3_read" {
  name = "${var.project_name}-sagemaker-s3-read-${var.environment}"
  role = aws_iam_role.sagemaker_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:ListBucket"
      ]
      Resource = [
        var.s3_diagrams_bucket_arn,
        "${var.s3_diagrams_bucket_arn}/*"
      ]
    }]
  })
}

# Acesso ao ECR para pull da imagem do container
resource "aws_iam_role_policy_attachment" "sagemaker_ecr_readonly" {
  role       = aws_iam_role.sagemaker_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# ─────────────────────────────────────────────
# SageMaker Model
# ─────────────────────────────────────────────
resource "aws_sagemaker_model" "llm" {
  name               = "${var.project_name}-llm-${var.environment}"
  execution_role_arn = aws_iam_role.sagemaker_execution_role.arn

  primary_container {
    image = var.model_container_image

    model_data_url = var.model_data_url != "" ? var.model_data_url : null

    environment = var.hf_model_id != "" ? {
      HF_MODEL_ID      = var.hf_model_id
      HF_TASK          = "text-generation"
      MAX_INPUT_LENGTH = "4096"
      MAX_TOTAL_TOKENS = "8192"
    } : {}
  }

  tags = var.common_tags
}

# ─────────────────────────────────────────────
# SageMaker Endpoint Configuration
# ─────────────────────────────────────────────
resource "aws_sagemaker_endpoint_configuration" "llm" {
  name = "${var.project_name}-llm-config-${var.environment}"

  production_variants {
    variant_name           = "primary"
    model_name             = aws_sagemaker_model.llm.name
    initial_instance_count = var.instance_count
    instance_type          = var.instance_type
  }

  tags = var.common_tags
}

# ─────────────────────────────────────────────
# SageMaker Endpoint
# ─────────────────────────────────────────────
resource "aws_sagemaker_endpoint" "llm" {
  name                 = "${var.project_name}-llm-${var.environment}"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.llm.name

  tags = var.common_tags
}
