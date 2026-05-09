environment = "prod"

# ─────────────────────────────────────────────
# Feature flags — habilitar módulos condicionais
# ─────────────────────────────────────────────
enable_networking     = true
enable_eks            = true
enable_sagemaker      = false
enable_yolo_sagemaker = true
enable_worker_iam     = true

# ─────────────────────────────────────────────
# Networking
# ─────────────────────────────────────────────
enable_ha_nat = false # false = 1 NAT Gateway (economia ~$32/mês)

# ─────────────────────────────────────────────
# EKS — mínimo para funcionar (economia)
# ─────────────────────────────────────────────
eks_node_instance_type = "t3.small"
eks_node_desired_size  = 1
eks_node_min_size      = 1
eks_node_max_size      = 2

# ─────────────────────────────────────────────
# Worker IAM (IRSA)
# ─────────────────────────────────────────────
k8s_namespace            = "prod"
k8s_service_account_name = "worker-service"

# ─────────────────────────────────────────────
# YOLO SageMaker
# ─────────────────────────────────────────────
yolo_sagemaker_model_data_url = "s3://tech-challenger-diagrams-prod-325066546876/models/yolo/model.tar.gz"
