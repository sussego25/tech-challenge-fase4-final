terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ─── Tabela: ArchitectureDiagram ───────────────────────────────────────────────

resource "aws_dynamodb_table" "diagrams" {
  name         = "${var.project_name}-diagrams-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "diagram_id"

  attribute {
    name = "diagram_id"
    type = "S"
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-diagrams-${var.environment}"
  })
}

