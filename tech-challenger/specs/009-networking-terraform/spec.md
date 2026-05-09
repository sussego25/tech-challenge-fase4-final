# Spec: 009 — VPC/Networking Terraform

**Feature Branch**: `009-networking-terraform`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: Criar módulo Terraform de VPC/Networking (subnets, SGs)

## Context
O pipeline de análise de diagramas precisa de uma VPC com subnets públicas e privadas para hospedar EKS, MSK (Kafka) e SageMaker. Atualmente os diretórios `infra/networking/terraform/` e `infra/networking/vpc/` estão **vazios**. Os módulos EKS e Kafka já existem mas recebem `vpc_id` e `subnet_ids` como variáveis externas — sem esse módulo, não há rede onde provisioná-los.

## Problem Statement
Precisamos de um módulo Terraform que:
1. Crie uma VPC dedicada ao projeto com CIDR configurável
2. Crie subnets públicas (2 AZs) para NAT Gateway e Load Balancers
3. Crie subnets privadas (2 AZs) para EKS nodes, MSK brokers e SageMaker
4. Provisione Internet Gateway, NAT Gateway(s) e Route Tables
5. Exporte VPC ID, subnet IDs e CIDRs para uso nos módulos EKS, Kafka e worker IAM
6. Integre ao módulo raiz `infra/terraform/main.tf`

## User Scenarios & Testing

### User Story 1 - VPC com isolamento de rede (Priority: P1)

O operador executa `terraform apply` e obtém uma VPC com subnets públicas e privadas isoladas, permitindo que EKS e MSK sejam provisionados em subnets privadas com acesso à internet via NAT.

**Why this priority**: Sem VPC, nenhum recurso de rede (EKS, MSK) pode ser criado. É pré-requisito de tudo.

**Independent Test**: `terraform plan` gera recursos de VPC, subnets, IGW, NAT e route tables sem erro.

**Acceptance Scenarios**:

1. **Given** o módulo networking é aplicado com `environment=dev`, **When** `terraform apply`, **Then** VPC criada com CIDR `10.0.0.0/16`, 2 subnets públicas e 2 privadas em AZs distintas
2. **Given** a VPC está criada, **When** um pod no EKS (subnet privada) tenta acessar a internet, **Then** o tráfego sai via NAT Gateway na subnet pública
3. **Given** o módulo é destruído, **When** `terraform destroy`, **Then** todos os recursos de rede são removidos sem dependências órfãs

---

### User Story 2 - Integração com módulos existentes (Priority: P1)

Os outputs do módulo networking alimentam automaticamente os módulos EKS e Kafka no `main.tf` raiz, eliminando a necessidade de passar VPC/subnet IDs manualmente.

**Why this priority**: Sem essa integração os módulos EKS e Kafka continuam recebendo strings vazias.

**Independent Test**: `terraform plan` do módulo raiz com `enable_eks=true` e `enable_kafka=true` resolve os IDs de VPC e subnets dos outputs do módulo networking.

**Acceptance Scenarios**:

1. **Given** o módulo networking está no `main.tf` raiz, **When** `enable_eks=true`, **Then** `module.eks` recebe `vpc_id` e `subnet_ids` do `module.networking`
2. **Given** o módulo networking está no `main.tf` raiz, **When** `enable_kafka=true`, **Then** `module.kafka` recebe `vpc_id`, `subnet_ids` e `allowed_cidr_blocks` do `module.networking`

---

### User Story 3 - Security Groups base (Priority: P2)

O módulo cria security groups base para isolar tráfego entre as camadas (EKS nodes, MSK brokers).

**Why this priority**: O MSK já cria seu próprio SG, mas precisamos de um SG para os EKS nodes que permita comunicação com MSK e SageMaker.

**Independent Test**: Após apply, security groups existem com regras de ingress/egress corretas.

**Acceptance Scenarios**:

1. **Given** a VPC está criada, **When** o módulo é aplicado, **Then** um SG `eks-nodes` permite egress para porta 9092 (Kafka) e 443 (SageMaker API)
2. **Given** o SG `eks-nodes` existe, **When** o módulo MSK é aplicado, **Then** `allowed_cidr_blocks` contém os CIDRs das subnets privadas

### Edge Cases

- O que acontece se a região não tiver 2 AZs disponíveis? → Erro de validação explícito
- O que acontece se o CIDR conflitar com VPCs existentes? → Responsabilidade do operador; documentar no README

## Requirements

### Functional Requirements

- **FR-001**: Módulo DEVE criar VPC com CIDR configurável (default `10.0.0.0/16`)
- **FR-002**: Módulo DEVE criar 2 subnets públicas em AZs distintas (CIDRs `10.0.1.0/24`, `10.0.2.0/24`)
- **FR-003**: Módulo DEVE criar 2 subnets privadas em AZs distintas (CIDRs `10.0.10.0/24`, `10.0.20.0/24`)
- **FR-004**: Módulo DEVE criar Internet Gateway associado à VPC
- **FR-005**: Módulo DEVE criar pelo menos 1 NAT Gateway em subnet pública com Elastic IP
- **FR-006**: Módulo DEVE criar route tables: pública (0.0.0.0/0 → IGW) e privada (0.0.0.0/0 → NAT)
- **FR-007**: Módulo DEVE exportar `vpc_id`, `public_subnet_ids`, `private_subnet_ids`, `private_subnet_cidrs`
- **FR-008**: Subnets públicas DEVEM ter `map_public_ip_on_launch = true`
- **FR-009**: Subnets privadas NÃO DEVEM ter IP público automático
- **FR-010**: Todos os recursos DEVEM receber tags `environment`, `project_name` e `common_tags`

### Key Entities

- **VPC**: Rede virtual isolada com DNS habilitado
- **Subnet**: Segmento de rede em uma AZ (pública ou privada)
- **NAT Gateway**: Permite subnets privadas acessarem internet sem exposição
- **Route Table**: Regras de roteamento para cada tipo de subnet

## Success Criteria

- **SC-001**: `terraform validate` e `terraform plan` passam sem erros
- **SC-002**: Após `apply`, EKS pode ser provisionado com os outputs do networking
- **SC-003**: Após `apply`, MSK pode ser provisionado com os outputs do networking
- **SC-004**: Pods em subnets privadas conseguem resolver DNS e acessar APIs AWS

## Clarifications

### Session 2026-04-18

- **Encryption**: Todos os recursos AWS usam chaves gerenciadas pela AWS (SSE-S3, SSE-DynamoDB, SSE-SQS, MSK TLS). Sem KMS customizado. VPC/subnets não precisam de configuração de criptografia adicional.
- **Observability**: CloudWatch only — JSON structured logs via Fluent Bit, CloudWatch Alarms para SQS depth/DLQ/errors. Sem Prometheus/Grafana.

## Assumptions

- Região `us-east-1` tem pelo menos 2 AZs (us-east-1a, us-east-1b)
- Um único NAT Gateway é suficiente para dev/staging (HA com 2 NATs é opcional via variável)
- CIDRs padrão não conflitam com redes existentes na conta AWS do usuário

## Technical Design

### Estrutura de módulo
```
infra/networking/terraform/
├── main.tf        # VPC, subnets, IGW, NAT, route tables
├── variables.tf   # vpc_cidr, environment, project_name, etc.
└── outputs.tf     # vpc_id, subnet IDs, CIDRs
```

### Integração no main.tf raiz
```hcl
module "networking" {
  source = "../networking/terraform"

  aws_region   = var.aws_region
  environment  = var.environment
  project_name = var.project_name
  common_tags  = var.common_tags
}

module "eks" {
  # ...
  vpc_id     = module.networking.vpc_id
  subnet_ids = module.networking.private_subnet_ids
}

module "kafka" {
  # ...
  vpc_id              = module.networking.vpc_id
  subnet_ids          = module.networking.private_subnet_ids
  allowed_cidr_blocks = module.networking.private_subnet_cidrs
}
```

### Fluxo de dependência
```
module "networking" (novo)
       ↓ outputs (vpc_id, subnet_ids, cidrs)
module "eks"    ← recebe vpc_id + private_subnet_ids
module "kafka"  ← recebe vpc_id + private_subnet_ids + cidrs
```

## Dependencies
- `infra/terraform/main.tf` — ponto de integração
- `infra/terraform/variables.tf` — nova variável `vpc_cidr` (default `10.0.0.0/16`)
- `infra/eks/terraform/` — consome `vpc_id` e `subnet_ids`
- `infra/kafka/terraform/` — consome `vpc_id`, `subnet_ids` e `allowed_cidr_blocks`

## Test / Validação
```powershell
cd tech-challenger/infra/terraform
terraform init
terraform validate
terraform plan -var="environment=dev"
```
