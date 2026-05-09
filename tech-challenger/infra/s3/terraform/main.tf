data "aws_caller_identity" "current" {}

locals {
  diagrams_bucket_name = "${var.project_name}-diagrams-${var.environment}-${data.aws_caller_identity.current.account_id}"
}

# -------------------------------------------------------------------
# Bucket principal de diagramas
# -------------------------------------------------------------------
resource "aws_s3_bucket" "diagrams" {
  bucket = local.diagrams_bucket_name

  tags = merge(var.common_tags, {
    Name        = local.diagrams_bucket_name
    Environment = var.environment
    Module      = "s3"
  })
}

# -------------------------------------------------------------------
# Bloquear todo acesso público
# -------------------------------------------------------------------
resource "aws_s3_bucket_public_access_block" "diagrams" {
  bucket = aws_s3_bucket.diagrams.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -------------------------------------------------------------------
# Versionamento
# -------------------------------------------------------------------
resource "aws_s3_bucket_versioning" "diagrams" {
  bucket = aws_s3_bucket.diagrams.id

  versioning_configuration {
    status = "Enabled"
  }
}

# -------------------------------------------------------------------
# Criptografia SSE-S3 (AES256)
# -------------------------------------------------------------------
resource "aws_s3_bucket_server_side_encryption_configuration" "diagrams" {
  bucket = aws_s3_bucket.diagrams.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# -------------------------------------------------------------------
# Lifecycle: expirar objetos apos N dias
# -------------------------------------------------------------------
resource "aws_s3_bucket_lifecycle_configuration" "diagrams" {
  bucket = aws_s3_bucket.diagrams.id

  rule {
    id     = "expire-diagrams"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = var.lifecycle_expiration_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  depends_on = [aws_s3_bucket_versioning.diagrams]
}
