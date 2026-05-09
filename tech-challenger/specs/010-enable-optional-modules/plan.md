# Plan: 010 — Habilitar EKS, Kafka e SageMaker

## Objective
Ativar os módulos opcionais (EKS, MSK, SageMaker) no Terraform raiz, conectar automaticamente outputs do networking e EKS OIDC, criar role IRSA do notification-service e adicionar permissão SageMaker na role do worker.

## Architecture Decisions
- Worker IAM auto-conecta OIDC do EKS quando `enable_eks=true` — elimina variáveis manuais `eks_oidc_provider_*`
- Role IRSA do notification-service segue o mesmo padrão do worker IAM, em sub-módulo separado `iam-notification/`
- Permissão SageMaker no worker é condicional: só adicionada quando `sagemaker_endpoint_arn != ""`
- `terraform.tfvars.example` serve de documentação viva — não é aplicado automaticamente
- Nova flag `enable_notification_iam` (default `false`) controla criação da role do notification-service

## Flow
```
terraform apply (infra/terraform/)
  ├─ module "networking"           → vpc_id, subnet_ids, cidrs
  ├─ module "sqs"                  → queue_url, queue_arn
  ├─ module "dynamodb"             → table_names, table_arns
  ├─ module "s3"                   → bucket_name, bucket_arn
  ├─ module "lambda_iam"           → role_arn (sem alteração)
  ├─ module "lambda"               → function_name, invoke_arn
  ├─ module "eks"[0]               → cluster, oidc_provider_arn/url
  ├─ module "worker_iam"[0]        → role_arn (+ sagemaker policy)
  │    └─ oidc auto-conectado ←── module.eks[0].oidc_provider_arn
  ├─ module "notification_iam"[0]  → role_arn (NOVO)
  │    └─ oidc auto-conectado ←── module.eks[0].oidc_provider_arn
  ├─ module "kafka"[0]             → bootstrap_brokers
  │    └─ vpc/subnets ←── module.networking.*
  └─ module "sagemaker"[0]         → endpoint_name, endpoint_arn
```

## Module Structure
```
infra/eks/terraform/iam-notification/    # NOVO
├── iam_role.tf     # IRSA role + dynamodb:PutItem na notifications table
├── variables.tf    # oidc, namespace, service_account, notifications_table_arn
└── outputs.tf      # notification_service_role_arn

infra/eks/terraform/iam/                 # MODIFICADO
└── iam_role.tf     # adicionar sagemaker:InvokeEndpoint (condicional)
    variables.tf    # adicionar sagemaker_endpoint_arn (optional)

infra/terraform/                         # MODIFICADO
├── main.tf         # wiring auto, module notification_iam
├── variables.tf    # enable_notification_iam, deprecar vpc/subnet vars manuais
├── outputs.tf      # notification_service_role_arn
└── terraform.tfvars.example  # NOVO — referência completa
```

## Implementation Steps

### Step 1 — Criar `infra/eks/terraform/iam-notification/variables.tf`
- `environment`, `project_name`, `common_tags`
- `eks_oidc_provider_arn`, `eks_oidc_provider_url`
- `k8s_namespace` (default `"default"`), `k8s_service_account_name` (default `"notification-service"`)
- `dynamodb_notifications_table_arn`

### Step 2 — Criar `infra/eks/terraform/iam-notification/iam_role.tf`
- `aws_iam_role "notification_service_role"` — trust policy IRSA idêntica ao worker
- `aws_iam_role_policy "notification_dynamodb_policy"` — `dynamodb:PutItem` na tabela notifications

### Step 3 — Criar `infra/eks/terraform/iam-notification/outputs.tf`
- `notification_service_role_arn`

### Step 4 — Expandir `infra/eks/terraform/iam/variables.tf`
- Adicionar `sagemaker_endpoint_arn` (default `""`)

### Step 5 — Expandir `infra/eks/terraform/iam/iam_role.tf`
- Adicionar `aws_iam_role_policy "worker_sagemaker_policy"` (condicional com `count = var.sagemaker_endpoint_arn != "" ? 1 : 0`)
- Actions: `sagemaker:InvokeEndpoint`
- Resource: `var.sagemaker_endpoint_arn`

### Step 6 — Atualizar `infra/terraform/variables.tf`
- Adicionar `enable_notification_iam` (bool, default `false`)
- Deprecar na description: `eks_vpc_id`, `eks_subnet_ids`, `kafka_vpc_id`, `kafka_subnet_ids`

### Step 7 — Atualizar `infra/terraform/main.tf`
- `module "eks"`: substituir `var.eks_vpc_id` → `module.networking.vpc_id`, `var.eks_subnet_ids` → `module.networking.private_subnet_ids`
- `module "kafka"`: substituir `var.kafka_vpc_id` → `module.networking.vpc_id`, `var.kafka_subnet_ids` → `module.networking.private_subnet_ids`, `var.kafka_allowed_cidr_blocks` → `module.networking.private_subnet_cidrs`
- `module "worker_iam"`: substituir `var.eks_oidc_provider_arn` → `module.eks[0].oidc_provider_arn`, adicionar `sagemaker_endpoint_arn = try(module.sagemaker[0].endpoint_arn, "")`
- Adicionar `module "notification_iam"` com `count = var.enable_notification_iam ? 1 : 0`, apontando para `../eks/terraform/iam-notification`

### Step 8 — Atualizar `infra/terraform/outputs.tf`
- Adicionar `notification_service_role_arn` (try null quando desabilitado)

### Step 9 — Criar `infra/terraform/terraform.tfvars.example`
- Todas as variáveis necessárias para ativação completa com comentários explicativos
- Valor placeholder `<ACCOUNT_ID>` onde aplicável

## Dependencies
- **Spec 009** — módulo networking deve existir para resolver `module.networking.*`
- `infra/dynamodb/terraform/` — ARN da tabela notifications (já existe)
- `infra/sagemaker/terraform/` — endpoint ARN (já existe)
- `infra/eks/terraform/iam/` — expandir (Steps 4-5)

## Validation
```powershell
cd tech-challenger/infra/terraform
terraform init -upgrade
terraform validate

# Plan com todos os módulos habilitados
terraform plan \
  -var="environment=dev" \
  -var="enable_eks=true" \
  -var="enable_worker_iam=true" \
  -var="enable_notification_iam=true" \
  -var="enable_kafka=true" \
  -var="enable_sagemaker=true" \
  -var="sagemaker_model_container_image=763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-tgi-inference:2.1.1-tgi1.4.0-gpu-py310-cu121-ubuntu22.04"
```
