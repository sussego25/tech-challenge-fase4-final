# Spec: 010 — Habilitar EKS, Kafka e SageMaker no Terraform

**Feature Branch**: `010-enable-optional-modules`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: Setar enable_eks=true, enable_kafka=true, enable_sagemaker=true e integrar com networking

## Context
Os módulos Terraform para EKS, Kafka (MSK) e SageMaker já estão **implementados** em `infra/eks/terraform/`, `infra/kafka/terraform/` e `infra/sagemaker/terraform/`. Porém, no `main.tf` raiz todas as flags estão `default = false`, os parâmetros de VPC/subnet são strings vazias, e o `module.eks` não alimenta automaticamente o `module.worker_iam`. Para que o pipeline funcione end-to-end na AWS, esses módulos precisam ser ativados e corretamente conectados.

## Problem Statement
Precisamos:
1. Criar um `terraform.tfvars` de referência (dev) com os flags habilitados
2. Conectar o output do módulo `networking` (spec 009) aos inputs de `eks`, `kafka` e `worker_iam`
3. Conectar o output do módulo `eks` ao `worker_iam` (OIDC provider) automaticamente
4. Adicionar uma role IRSA para o notification-service (acesso DynamoDB notifications)
5. Adicionar permissão de `sagemaker:InvokeEndpoint` na role do worker

## User Scenarios & Testing

### User Story 1 - Ativação integrada dos módulos (Priority: P1)

O operador cria um `terraform.tfvars` com `enable_eks=true`, `enable_kafka=true`, `enable_sagemaker=true` e executa `terraform plan`. Todos os módulos resolvem suas dependências automaticamente via outputs do networking e EKS.

**Why this priority**: Sem ativar esses módulos, não há cluster, mensageria nem LLM.

**Independent Test**: `terraform plan` com os flags habilitados gera todos os recursos sem erro de variável faltante.

**Acceptance Scenarios**:

1. **Given** `enable_eks=true` e módulo networking ativo, **When** `terraform plan`, **Then** EKS usa `module.networking.vpc_id` e `module.networking.private_subnet_ids`
2. **Given** `enable_eks=true` e `enable_worker_iam=true`, **When** `terraform plan`, **Then** `worker_iam` usa `module.eks[0].oidc_provider_arn` automaticamente
3. **Given** `enable_kafka=true` e módulo networking ativo, **When** `terraform plan`, **Then** MSK usa `module.networking.vpc_id` e CIDRs privados para SG

---

### User Story 2 - IAM do worker com SageMaker (Priority: P1)

O worker-service precisa invocar o endpoint SageMaker. A role IRSA do worker deve incluir `sagemaker:InvokeEndpoint`.

**Why this priority**: Sem essa permissão, o worker recebe AccessDenied ao chamar SageMaker.

**Acceptance Scenarios**:

1. **Given** `enable_sagemaker=true` e `enable_worker_iam=true`, **When** `terraform plan`, **Then** a role do worker inclui policy com `sagemaker:InvokeEndpoint` no ARN do endpoint SageMaker

---

### User Story 3 - IRSA para notification-service (Priority: P1)

O notification-service roda no EKS e precisa de acesso DynamoDB (tabela notifications). Hoje não existe role IRSA para ele.

**Why this priority**: Sem IAM role, o notification-service não consegue salvar notificações.

**Acceptance Scenarios**:

1. **Given** `enable_worker_iam=true` (ou nova flag `enable_notification_iam`), **When** `terraform plan`, **Then** role IRSA `notification-service` com `dynamodb:PutItem` na tabela notifications é criada
2. **Given** a role IRSA está criada, **When** o Helm chart do notification-service referencia o ARN, **Then** o pod assume a role via IRSA

### Edge Cases

- O que acontece se `enable_eks=true` mas networking não está provisionado? → `terraform plan` falha com erro claro de subnet vazio
- O que acontece se `enable_sagemaker=true` sem `model_container_image`? → Já falha na validação do SageMaker module (variável obrigatória sem default)

## Requirements

### Functional Requirements

- **FR-001**: `main.tf` DEVE passar `module.networking.vpc_id` e `module.networking.private_subnet_ids` para `module.eks` quando ambos estão habilitados
- **FR-002**: `main.tf` DEVE passar `module.networking.vpc_id`, `module.networking.private_subnet_ids` e `module.networking.private_subnet_cidrs` para `module.kafka`
- **FR-003**: `main.tf` DEVE passar `module.eks[0].oidc_provider_arn` e `module.eks[0].oidc_provider_url` para `module.worker_iam` quando `enable_eks=true`
- **FR-004**: Role IRSA do worker DEVE incluir policy `sagemaker:InvokeEndpoint` com resource do endpoint SageMaker
- **FR-005**: DEVE existir um módulo IAM para notification-service com `dynamodb:PutItem` na tabela notifications
- **FR-006**: DEVE existir um arquivo `terraform.tfvars.example` com todos os valores necessários para ativação completa
- **FR-007**: Variáveis `eks_vpc_id`, `eks_subnet_ids`, `kafka_vpc_id`, `kafka_subnet_ids` DEVEM ser removidas ou deprecadas em favor dos outputs do networking

### Key Entities

- **IRSA Role (worker)**: Permite o worker-service acessar SQS, DynamoDB, S3 e SageMaker
- **IRSA Role (notification)**: Permite o notification-service acessar DynamoDB notifications
- **terraform.tfvars**: Arquivo de configuração com variáveis do ambiente

## Success Criteria

- **SC-001**: `terraform plan` com todos os flags habilitados gera plano válido sem erros
- **SC-002**: Role do worker inclui permissão SageMaker `InvokeEndpoint`
- **SC-003**: Role do notification-service existe com permissão DynamoDB `PutItem`
- **SC-004**: Nenhuma variável manual de VPC/subnet é necessária quando networking está ativo

## Assumptions

- Módulo networking (spec 009) já está implementado e disponível
- Conta AWS tem quota para EKS, MSK e SageMaker na região escolhida
- O namespace Kubernetes será `default` por padrão para ambos os services

## Technical Design

### Mudanças no main.tf raiz

```hcl
# Substitui vars manuais por outputs do networking
module "eks" {
  count      = var.enable_eks ? 1 : 0
  vpc_id     = module.networking.vpc_id
  subnet_ids = module.networking.private_subnet_ids
  # ... demais vars mantidas
}

module "kafka" {
  count               = var.enable_kafka ? 1 : 0
  vpc_id              = module.networking.vpc_id
  subnet_ids          = module.networking.private_subnet_ids
  allowed_cidr_blocks = module.networking.private_subnet_cidrs
  # ... demais vars mantidas
}

module "worker_iam" {
  count                 = var.enable_worker_iam ? 1 : 0
  eks_oidc_provider_arn = module.eks[0].oidc_provider_arn
  eks_oidc_provider_url = replace(module.eks[0].oidc_provider_url, "https://", "")
  sagemaker_endpoint_arn = try(module.sagemaker[0].endpoint_arn, "")
  # ... demais vars mantidas
}

module "notification_iam" {
  count  = var.enable_notification_iam ? 1 : 0
  source = "../eks/terraform/iam-notification"
  # ... IRSA com dynamodb:PutItem na notifications table
}
```

### Nova estrutura IAM
```
infra/eks/terraform/iam/                    # worker-service (existente)
  iam_role.tf  ← adicionar sagemaker:InvokeEndpoint
  variables.tf ← adicionar sagemaker_endpoint_arn

infra/eks/terraform/iam-notification/       # notification-service (novo)
  iam_role.tf
  variables.tf
  outputs.tf
```

### terraform.tfvars.example
```hcl
environment  = "dev"
project_name = "tech-challenger"
aws_region   = "us-east-1"

# Networking (spec 009 cria automaticamente)
# vpc_cidr = "10.0.0.0/16"

# Habilitar módulos
enable_eks              = true
enable_worker_iam       = true
enable_notification_iam = true
enable_kafka            = true
enable_sagemaker        = true

# SageMaker
sagemaker_model_container_image = "763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-tgi-inference:2.1.1-tgi1.4.0-gpu-py310-cu121-ubuntu22.04"
sagemaker_hf_model_id           = "mistralai/Mistral-7B-Instruct-v0.2"
sagemaker_instance_type         = "ml.g4dn.xlarge"
```

## Clarifications

### Session 2026-04-18

- **Encryption**: Todos os recursos usam chaves gerenciadas pela AWS (SSE-S3, SSE-DynamoDB, SSE-SQS, MSK TLS). Não é necessário criar ou gerenciar chaves KMS customizadas. Nenhuma policy KMS nos módulos IAM.
- **Observability**: CloudWatch only — JSON structured logs via Fluent Bit, CloudWatch Alarms. Sem Prometheus/Grafana.
- **`user_id` vs `user_email`**: `user_id` é UUID. Adicionar campo `user_email` nos shared contracts/events para uso pelo notification-service como destino SES. Lambda handler extrai `user_email` do request e propaga nos eventos.

## Dependencies
- **Spec 009** (networking-terraform) — outputs de VPC e subnets
- `infra/terraform/main.tf` — ponto de integração
- `infra/eks/terraform/iam/` — modificar para adicionar SageMaker
- `infra/dynamodb/terraform/` — ARN da tabela notifications

## Test / Validação
```powershell
cd tech-challenger/infra/terraform
terraform init
terraform validate
terraform plan -var-file="terraform.tfvars.example"
```
