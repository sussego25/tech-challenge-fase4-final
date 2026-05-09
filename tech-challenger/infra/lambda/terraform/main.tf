locals {
  function_name    = "${var.project_name}-order-handler-${var.environment}"
  handler_src_path = abspath("${path.module}/../../../services/lambda-functions/order-handler")
  shared_path      = abspath("${path.module}/../../../shared")
  build_path       = abspath("${path.module}/build")
}

# -------------------------------------------------------------------
# Prepara diretorio de build com handler + contracts + libs + deps
# -------------------------------------------------------------------
resource "null_resource" "build_lambda_package" {
  triggers = {
    handler_src  = sha256(join("", [for f in fileset(local.handler_src_path, "**/*.py") : filesha256("${local.handler_src_path}/${f}")]))
    shared_src   = sha256(join("", [for f in fileset(local.shared_path, "**/*.py") : filesha256("${local.shared_path}/${f}")]))
    requirements = filesha256("${local.handler_src_path}/requirements.txt")
    build_script = filesha256("${path.module}/../build_package.py")
  }

  provisioner "local-exec" {
    working_dir = "${path.module}/.."
    command     = "python3 build_package.py"
  }
}

# -------------------------------------------------------------------
# Empacota o build em um zip
# -------------------------------------------------------------------
data "archive_file" "order_handler" {
  type        = "zip"
  source_dir  = local.build_path
  output_path = "${path.module}/lambda_order_handler.zip"
  depends_on  = [null_resource.build_lambda_package]

  excludes = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
  ]
}

# -------------------------------------------------------------------
# Lambda Function
# -------------------------------------------------------------------
resource "aws_lambda_function" "order_handler" {
  function_name = local.function_name
  description   = "Order handler para upload e processamento de diagramas de arquitetura"
  role          = var.lambda_role_arn

  filename         = data.archive_file.order_handler.output_path
  source_code_hash = data.archive_file.order_handler.output_base64sha256

  runtime     = "python3.11"
  handler     = "handler.lambda_handler"
  timeout     = 30
  memory_size = 256

  environment {
    variables = {
      S3_BUCKET      = var.s3_bucket_name
      SQS_QUEUE_URL  = var.sqs_queue_url
      DYNAMODB_TABLE = var.dynamodb_table_name
    }
  }

  tags = merge(var.common_tags, {
    Name        = local.function_name
    Environment = var.environment
    Module      = "lambda"
  })
}

# -------------------------------------------------------------------
# Permissão para o S3 invocar a Lambda via event notification
# -------------------------------------------------------------------
resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.order_handler.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.s3_bucket_arn
}
