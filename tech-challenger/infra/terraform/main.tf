terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    bucket = "tech-challenger-tfstate-325066546876"
    key    = "infra/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  yolo_sagemaker_model_container_image = (
    var.yolo_sagemaker_model_container_image != ""
    ? var.yolo_sagemaker_model_container_image
    : "${module.ecr.repository_urls["yolo-inference"]}:latest"
  )
}

module "sqs" {
  source = "../sqs/terraform"

  aws_region   = var.aws_region
  environment  = var.environment
  project_name = var.project_name
  common_tags  = var.common_tags
}

module "sns" {
  source = "../sns/terraform"

  environment  = var.environment
  project_name = var.project_name
  common_tags  = var.common_tags
}

module "dynamodb" {
  source = "../dynamodb/terraform"

  aws_region   = var.aws_region
  environment  = var.environment
  project_name = var.project_name
  common_tags  = var.common_tags
}

module "s3" {
  source = "../s3/terraform"

  aws_region                = var.aws_region
  environment               = var.environment
  project_name              = var.project_name
  common_tags               = var.common_tags
  lifecycle_expiration_days = var.s3_lifecycle_expiration_days
}

module "lambda_iam" {
  source = "../lambda/terraform/iam"

  environment                 = var.environment
  project_name                = var.project_name
  sqs_queue_arn               = module.sqs.architecture_analysis_queue_arn
  dynamodb_diagrams_table_arn = module.dynamodb.diagrams_table_arn
  s3_diagrams_bucket_arn      = module.s3.diagrams_bucket_arn
  common_tags                 = var.common_tags
}

module "lambda" {
  source = "../lambda/terraform"

  environment         = var.environment
  project_name        = var.project_name
  common_tags         = var.common_tags
  lambda_role_arn     = module.lambda_iam.lambda_documents_role_arn
  s3_bucket_name      = module.s3.diagrams_bucket_name
  s3_bucket_arn       = module.s3.diagrams_bucket_arn
  sqs_queue_url       = module.sqs.architecture_analysis_queue_url
  dynamodb_table_name = module.dynamodb.diagrams_table_name
}

# -------------------------------------------------------------------
# S3 Event Notification: aciona Lambda ao fazer upload no bucket
# Definido aqui (e nao no modulo s3) para evitar dependencia circular
# -------------------------------------------------------------------
resource "aws_s3_bucket_notification" "diagrams_trigger" {
  bucket = module.s3.diagrams_bucket_name

  lambda_function {
    lambda_function_arn = module.lambda.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "diagrams/"
  }

  depends_on = [module.lambda]
}

module "worker_iam" {
  count  = var.enable_worker_iam ? 1 : 0
  source = "../eks/terraform/iam"

  environment                 = var.environment
  project_name                = var.project_name
  eks_oidc_provider_arn       = var.enable_eks ? module.eks[0].oidc_provider_arn : var.eks_oidc_provider_arn
  eks_oidc_provider_url       = var.enable_eks ? replace(module.eks[0].oidc_provider_url, "https://", "") : replace(var.eks_oidc_provider_url, "https://", "")
  k8s_namespace               = var.k8s_namespace
  k8s_service_account_name    = var.k8s_service_account_name
  sqs_queue_arn               = module.sqs.architecture_analysis_queue_arn
  sqs_dlq_arn                 = module.sqs.architecture_analysis_dlq_arn
  sns_topic_arn               = module.sns.analysis_results_topic_arn
  dynamodb_diagrams_table_arn = module.dynamodb.diagrams_table_arn
  s3_diagrams_bucket_arn      = module.s3.diagrams_bucket_arn
  common_tags                 = var.common_tags
}

module "networking" {
  count  = var.enable_networking ? 1 : 0
  source = "../networking/terraform"

  aws_region    = var.aws_region
  environment   = var.environment
  project_name  = var.project_name
  common_tags   = var.common_tags
  vpc_cidr      = var.vpc_cidr
  enable_ha_nat = var.enable_ha_nat
}

module "eks" {
  count  = var.enable_eks ? 1 : 0
  source = "../eks/terraform"

  aws_region         = var.aws_region
  environment        = var.environment
  project_name       = var.project_name
  common_tags        = var.common_tags
  cluster_version    = var.eks_cluster_version
  vpc_id             = var.enable_networking ? module.networking[0].vpc_id : var.eks_vpc_id
  subnet_ids         = var.enable_networking ? module.networking[0].private_subnet_ids : var.eks_subnet_ids
  node_instance_type = var.eks_node_instance_type
  node_desired_size  = var.eks_node_desired_size
  node_min_size      = var.eks_node_min_size
  node_max_size      = var.eks_node_max_size
}

module "sagemaker" {
  count  = var.enable_sagemaker ? 1 : 0
  source = "../sagemaker/terraform"

  aws_region             = var.aws_region
  environment            = var.environment
  project_name           = var.project_name
  common_tags            = var.common_tags
  s3_diagrams_bucket_arn = module.s3.diagrams_bucket_arn
  model_container_image  = var.sagemaker_model_container_image
  model_data_url         = var.sagemaker_model_data_url
  hf_model_id            = var.sagemaker_hf_model_id
  instance_type          = var.sagemaker_instance_type
  instance_count         = var.sagemaker_instance_count
}

module "yolo_sagemaker" {
  count  = var.enable_yolo_sagemaker ? 1 : 0
  source = "../yolo-sagemaker/terraform"

  environment            = var.environment
  project_name           = var.project_name
  common_tags            = var.common_tags
  s3_diagrams_bucket_arn = module.s3.diagrams_bucket_arn
  model_container_image  = local.yolo_sagemaker_model_container_image
  model_data_url         = var.yolo_sagemaker_model_data_url
  instance_type          = var.yolo_sagemaker_instance_type
  instance_count         = var.yolo_sagemaker_instance_count
}

module "ecr" {
  source = "../ecr/terraform"

  environment           = var.environment
  project_name          = var.project_name
  repository_names      = var.ecr_repository_names
  image_retention_count = var.ecr_image_retention_count
  common_tags           = var.common_tags
}
