resource "aws_iam_role" "yolo_execution_role" {
  name = "${var.project_name}-yolo-sagemaker-execution-${var.environment}"

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
  role       = aws_iam_role.yolo_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

resource "aws_iam_role_policy_attachment" "sagemaker_ecr_readonly" {
  role       = aws_iam_role.yolo_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy" "sagemaker_s3_read" {
  name = "${var.project_name}-yolo-sagemaker-s3-read-${var.environment}"
  role = aws_iam_role.yolo_execution_role.id

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

resource "aws_sagemaker_model" "yolo" {
  name               = "${var.project_name}-yolo-${var.environment}"
  execution_role_arn = aws_iam_role.yolo_execution_role.arn

  primary_container {
    image          = var.model_container_image
    model_data_url = var.model_data_url

    environment = {
      SAGEMAKER_PROGRAM = "inference.py"
    }
  }

  tags = var.common_tags
}

resource "aws_sagemaker_endpoint_configuration" "yolo" {
  name = "${var.project_name}-yolo-config-${var.environment}"

  production_variants {
    variant_name           = "primary"
    model_name             = aws_sagemaker_model.yolo.name
    initial_instance_count = var.instance_count
    instance_type          = var.instance_type
  }

  tags = var.common_tags
}

resource "aws_sagemaker_endpoint" "yolo" {
  name                 = "${var.project_name}-yolo-${var.environment}"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.yolo.name

  tags = var.common_tags
}
